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

# 获取脚本所在目录（绝对路径）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def screenshot_merchant_hd(output_path=None):
    """
    高清截图远行商人页面（只包含商品列表和时间选择，不包含底部工具栏）
    默认将截图保存在脚本所在目录下的 merchant_hd.png
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

            # 隐藏底部工具栏和顶部 sw-box 工具栏
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
            return output_path
    except (PlaywrightTimeoutError, Exception) as e:
        print(f"截图失败: {e}")
        return None


def delete_all_gitee_images(repo_owner, repo_name, access_token, branch="master", folder="images"):
    """删除 Gitee 仓库指定文件夹下所有 merchant_hd 开头的图片"""
    try:
        url = f"https://gitee.com/api/v5/repos/{repo_owner}/{repo_name}/contents/{folder}?access_token={access_token}"
        files = requests.get(url).json()
        image_files = [f for f in files if isinstance(f, dict) and f.get("type") == "file" and f.get("name", "").startswith("merchant_hd_") and f.get("name", "").endswith(".png")]

        print(f"找到 {len(image_files)} 个 merchant_hd 图片文件，准备全部删除")
        for f in image_files:
            filename = f["name"]
            sha = f.get("sha")
            if not sha:
                print(f"无法获取 {filename} 的 SHA，跳过")
                continue
            delete_url = f"https://gitee.com/api/v5/repos/{repo_owner}/{repo_name}/contents/{folder}/{filename}"
            delete_data = {"access_token": access_token, "message": f"Delete {filename}", "sha": sha, "branch": branch}
            resp = requests.delete(delete_url, json=delete_data)
            print(f"删除 {filename}: {'成功' if resp.status_code == 200 else f'失败 {resp.status_code}'}")
    except Exception as e:
        print(f"删除 Gitee 图片时出错: {e}")


def upload_to_gitee(image_path, repo_owner, repo_name, access_token, branch="master", folder="images"):
    """上传图片到 Gitee 仓库并返回图片链接"""
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        ext = os.path.splitext(os.path.basename(image_path))[1]
        filename = f"{base_name}_{int(time.time())}{ext}"
        filepath = f"{folder}/{filename}"

        api_url = f"https://gitee.com/api/v5/repos/{repo_owner}/{repo_name}/contents/{filepath}"
        data = {"access_token": access_token, "message": f"Update {filename}", "content": base64.b64encode(image_data).decode('utf-8'), "branch": branch}

        check_resp = requests.get(f"{api_url}?access_token={access_token}")
        if check_resp.status_code == 200:
            file_info = check_resp.json()
            if isinstance(file_info, dict) and "sha" in file_info:
                data["sha"] = file_info["sha"]
                print(f"文件已存在，使用 SHA: {file_info['sha']}")

        resp = requests.put(api_url, json=data) if "sha" in data else requests.post(api_url, json=data)
        resp.raise_for_status()
        result = resp.json()

        download_url = result.get("content", {}).get("download_url") or result.get("download_url") or result.get("html_url")
        if not download_url:
            download_url = f"https://gitee.com/{repo_owner}/{repo_name}/raw/{branch}/{filepath}"
        print(f"上传成功: {download_url}")
        return download_url
    except Exception as e:
        print(f"上传失败: {e}")
        return None


def send_image_to_dingtalk(image_path):
    """发送图片到钉钉，成功后删除 Gitee 上所有相关图片及本地截图"""
    try:
        # 从环境变量获取配置
        webhook = os.getenv('DINGTALK_WEBHOOK')
        secret = os.getenv('DINGTALK_SECRET')
        repo_owner = os.getenv('GITEE_OWNER')
        repo_name = os.getenv('GITEE_REPO')
        access_token = os.getenv('GITEE_TOKEN')

        # 检查环境变量是否设置
        if not all([webhook, secret, repo_owner, repo_name, access_token]):
            print("错误：缺少必要的环境变量配置")
            print("请设置以下环境变量：")
            print("- DINGTALK_WEBHOOK: 钉钉机器人 Webhook")
            print("- DINGTALK_SECRET: 钉钉机器人 Secret")
            print("- GITEE_OWNER: Gitee 仓库所有者")
            print("- GITEE_REPO: Gitee 仓库名")
            print("- GITEE_TOKEN: Gitee 访问令牌")
            return False

        image_url = upload_to_gitee(image_path, repo_owner, repo_name, access_token)
        if not image_url:
            print("上传图片失败，无法发送")
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
            print("钉钉发送成功")
        else:
            print(f"钉钉发送失败: {result.get('errmsg')}")

        # 删除所有 Gitee 图片及本地截图
        delete_all_gitee_images(repo_owner, repo_name, access_token, "master", "images")
        if os.path.exists(image_path):
            os.remove(image_path)
            print(f"已删除本地截图: {image_path}")

        return result.get("errcode") == 0
    except Exception as e:
        print(f"发送过程出错: {e}")
        if os.path.exists(image_path):
            os.remove(image_path)
        return False


if __name__ == "__main__":
    img = screenshot_merchant_hd()
    if img:
        send_image_to_dingtalk(img)
    else:
        print("截图失败，流程终止")