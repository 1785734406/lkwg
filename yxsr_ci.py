#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub Actions 专用脚本 - 使用环境变量配置敏感信息"""

import time
import requests
import base64
import os
import hmac
import hashlib
import urllib.parse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def screenshot_merchant_hd(output_path=None):
    """
    高清截图远行商人页面
    返回截图路径和是否有强烈推荐物品
    """
    if output_path is None:
        output_path = os.path.join(SCRIPT_DIR, "merchant_hd.png")
    try:
        url = os.getenv('LKWG_URL', "https://www.onebiji.com/hykb_tools/comm/lkwgmerchant/preview.php?id=1&immgj=0&imm=1")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            context = browser.new_context(
                viewport={"width": 750, "height": 2000},
                device_scale_factor=1,
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
                locale="zh-CN",
                timezone_id="Asia/Shanghai"
            )
            page = context.new_page()
            page.goto(url, timeout=150000)
            page.wait_for_selector(".shop-box", timeout=100000)
            page.wait_for_selector(".shop-list", timeout=80000)
            page.wait_for_selector(".shop-list li", timeout=80000, state="attached")

            # 检测商品列表是否为空（.show_none_tip 元素可见即为空列表）
            has_empty_tip = page.locator(".show_none_tip").first.is_visible()
            
            # 检测是否有商品显示"已结束"状态（.time-un 元素存在表示有过期商品）
            has_expired = page.locator(".time-un").count() > 0
            
            # 任一个条件满足都进入等待
            is_empty = has_empty_tip or has_expired
            
            # 如果商品列表为空或有已结束商品，等待重试（最多等待10分钟，每30秒检查一次）
            retry_count = 0
            max_retries = 20  # 最多重试20次，每次30秒，总共10分钟
            while is_empty and retry_count < max_retries:
                print(f"商品列表为空或有已结束商品，等待重试 ({retry_count + 1}/{max_retries})")
                time.sleep(30)
                page.reload()
                page.wait_for_selector(".shop-list li", timeout=80000, state="attached")
                has_empty_tip = page.locator(".show_none_tip").first.is_visible()
                has_expired = page.locator(".time-un").count() > 0
                is_empty = has_empty_tip or has_expired
                retry_count += 1
            
            if is_empty:
                print("等待超时，商品列表仍为空")
                browser.close()
                return None, False

            # 检测是否有强烈推荐物品（只检测可见商品中的 tp2，忽略 display:none 的商品）
            has_recommend = False
            items = page.locator(".shop-list li").all()
            for item in items:
                if item.is_visible():
                    if item.locator(".tp2").count() > 0:
                        has_recommend = True
                        break
            print(f"强烈推荐物品检测: {'有' if has_recommend else '无'}")

            # 隐藏版本更新弹窗（通过 ID 直接隐藏）
            try:
                page.evaluate("if (document.querySelector('#shop_rules')) document.querySelector('#shop_rules').style.display = 'none';")
            except Exception:
                pass
            
            # 隐藏底部工具栏，顶部 sw-box 工具栏
            try:
                page.evaluate("if (document.querySelector('.tab')) document.querySelector('.tab').style.display = 'none';")
                page.evaluate("if (document.querySelector('.share-bom')) document.querySelector('.share-bom').style.display = 'none';")
                page.evaluate("if (document.querySelector('.sw-box')) document.querySelector('.sw-box').style.display = 'none';")
            except Exception:
                pass
            time.sleep(10)
            content = page.locator(".content")
            content.screenshot(path=output_path, type="png")
            browser.close()
            print(f"高清截图已保存至: {output_path}")
            return output_path, has_recommend
    except (PlaywrightTimeoutError, Exception) as e:
        print(f"截图失败: {e}")
        return None, False


def upload_to_picgo(image_path, api_key):
    """上传图片到 PicGo Chevereto API 并返回图片链接"""
    try:
        api_url = "https://www.picgo.net/api/1/upload"
        
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        files = {
            'source': ('merchant_hd.png', image_data, 'image/png')
        }
        
        data = {
            'expiration': 'PT4H'
        }
        
        headers = {
            'X-API-Key': api_key
        }
        
        resp = requests.post(api_url, files=files, data=data, headers=headers)
        resp.raise_for_status()
        result = resp.json()
        
        if result.get('status_code') == 200:
            image_url = result.get('image', {}).get('url')
            if image_url:
                print(f"上传成功: {image_url}")
                print("图片将在4小时后自动删除")
                return image_url
            else:
                print("上传成功但未返回图片URL")
                return None
        else:
            print(f"上传失败: {result.get('error', {}).get('message', '未知错误')}")
            return None
    except Exception as e:
        print(f"上传失败: {e}")
        return None


def send_image_to_dingtalk(image_url):
    """发送图片链接到第一个钉钉群（全物品群）"""
    try:
        webhook = os.getenv('DINGTALK_WEBHOOK')
        secret = os.getenv('DINGTALK_SECRET')

        if not webhook or not secret:
            print("错误：缺少 DINGTALK_WEBHOOK 或 DINGTALK_SECRET 环境变量")
            return False

        timestamp = str(int(time.time() * 1000))
        sign = urllib.parse.quote_plus(base64.b64encode(hmac.new(secret.encode('utf-8'), f"{timestamp}\n{secret}".encode('utf-8'), hashlib.sha256).digest()))
        webhook_url = f"{webhook}&timestamp={timestamp}&sign={sign}"

        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": "远行商人商品列表",
                "text": f"远行商人商品列表定时推送中，当前商品信息：\n ![远行商人商品列表]({image_url})"
            },
            "at": {"isAtAll": False}
        }
        resp = requests.post(webhook_url, json=data, headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        result = resp.json()
        if result.get("errcode") == 0:
            print("全物品群通知发送成功")
            return True
        else:
            print(f"全物品群通知发送失败: {result.get('errmsg')}")
            return False
    except Exception as e:
        print(f"发送过程出错: {e}")
        return False


def send_recommend_to_dingtalk(image_url):
    """向第二个钉钉群发送强烈推荐物品通知（推荐群）"""
    try:
        webhook = os.getenv('DINGTALK2_WEBHOOK')
        secret = os.getenv('DINGTALK2_SECRET')

        if not webhook or not secret:
            print("错误：缺少 DINGTALK2_WEBHOOK 或 DINGTALK2_SECRET 环境变量")
            return False

        timestamp = str(int(time.time() * 1000))
        sign = urllib.parse.quote_plus(base64.b64encode(hmac.new(secret.encode('utf-8'), f"{timestamp}\n{secret}".encode('utf-8'), hashlib.sha256).digest()))
        webhook_url = f"{webhook}&timestamp={timestamp}&sign={sign}"

        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": "远行商人强烈推荐",
                "text": f"⚠️ 发现强烈推荐购买物品！\n ![远行商人商品列表]({image_url})"
            },
            "at": {"isAtAll": False}
        }
        resp = requests.post(webhook_url, json=data, headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        result = resp.json()
        if result.get("errcode") == 0:
            print("推荐群通知发送成功")
            return True
        else:
            print(f"推荐群通知发送失败: {result.get('errmsg')}")
            return False
    except Exception as e:
        print(f"发送强烈推荐通知出错: {e}")
        return False


if __name__ == "__main__":
    picgo_api_key = os.getenv('PICGO_API_KEY')

    if not picgo_api_key:
        print("错误：缺少 PICGO_API_KEY 环境变量")
        exit(1)

    img, has_recommend = screenshot_merchant_hd()
    if img:
        image_url = upload_to_picgo(img, picgo_api_key)
        if image_url:
            # 发送全物品群前等待10秒
            time.sleep(10)
            send_image_to_dingtalk(image_url)
            
            # 再发送推荐群（如果有强烈推荐物品）
            if has_recommend:
                send_recommend_to_dingtalk(image_url)
            else:
                print("无强烈推荐物品，跳过推荐群通知")

        if os.path.exists(img):
            os.remove(img)
            print(f"已删除本地截图: {img}")
    else:
        print("截图失败，流程终止")