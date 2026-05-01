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
    
    max_retries = 3  # 最大重试次数
    retry_delay = 5  # 重试间隔（秒）
    
    for attempt in range(max_retries):
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
                
                print(f"尝试第 {attempt + 1}/{max_retries} 次加载页面...")
                # 移除超时限制，让页面有足够时间加载
                page.goto(url, timeout=0)
                
                # 增加等待选择器的超时时间
                page.wait_for_selector(".shop-box", timeout=30000)
                page.wait_for_selector(".shop-list", timeout=20000)
                page.wait_for_selector(".shop-list li", timeout=20000, state="attached")

                # 隐藏底部工具栏
                try:
                    page.evaluate("if (document.querySelector('.tab')) document.querySelector('.tab').style.display = 'none';")
                    page.evaluate("if (document.querySelector('.share-bom')) document.querySelector('.share-bom').style.display = 'none';")
                except Exception:
                    pass
                
                time.sleep(10)
                content = page.locator(".content")
                content.screenshot(path=output_path, type="png")
                browser.close()
                print(f"高清截图已保存至: {output_path}")
                return output_path
                
        except PlaywrightTimeoutError as e:
            print(f"第 {attempt + 1} 次尝试失败: 超时 - {e}")
            if attempt < max_retries - 1:
                print(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
            else:
                print("已达到最大重试次数，截图失败")
                return None
        except Exception as e:
            print(f"第 {attempt + 1} 次尝试失败: {e}")
            if attempt < max_retries - 1:
                print(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
            else:
                print("已达到最大重试次数，截图失败")
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

        resp = requests.put(api_url, json=data)
        if resp.status_code in [200, 201]:
            result = resp.json()
            download_url = f"https://gitee.com/{repo_owner}/{repo_name}/raw/{branch}/{filepath}"
            print(f"图片上传成功: {download_url}")
            return download_url
        else:
            print(f"图片上传失败: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"上传 Gitee 图片时出错: {e}")
        return None


def send_image_to_dingtalk(webhook_url, secret, image_url, message="今日远行商人商品信息"):
    """发送图片到钉钉群"""
    try:
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode('utf-8')
        string_to_sign = f"{timestamp}\n{secret}"
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote(base64.b64encode(hmac_code))

        url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"
        headers = {"Content-Type": "application/json"}
        data = {
            "msgtype": "link",
            "link": {
                "text": message,
                "title": "远行商人",
                "picUrl": image_url,
                "messageUrl": image_url
            }
        }

        resp = requests.post(url, headers=headers, json=data)
        if resp.status_code == 200:
            result = resp.json()
            if result.get("errcode") == 0:
                print("钉钉消息发送成功")
                return True
            else:
                print(f"钉钉消息发送失败: {result.get('errmsg')}")
                return False
        else:
            print(f"钉钉消息发送失败: {resp.status_code}")
            return False
    except Exception as e:
        print(f"发送钉钉消息时出错: {e}")
        return False


def main():
    print("=== 开始执行截图任务 ===")
    
    # 获取环境变量
    dingtalk_webhook = os.getenv('DINGTALK_WEBHOOK')
    dingtalk_secret = os.getenv('DINGTALK_SECRET')
    gitee_owner = os.getenv('GITEE_OWNER')
    gitee_repo = os.getenv('GITEE_REPO')
    gitee_token = os.getenv('GITEE_TOKEN')
    
    # 打印环境变量状态
    print(f"DINGTALK_WEBHOOK set: {bool(dingtalk_webhook)}")
    print(f"DINGTALK_SECRET set: {bool(dingtalk_secret)}")
    print(f"GITEE_OWNER set: {bool(gitee_owner)}")
    print(f"GITEE_REPO set: {bool(gitee_repo)}")
    print(f"GITEE_TOKEN set: {bool(gitee_token)}")

    # 截图
    image_path = screenshot_merchant_hd()
    if not image_path:
        print("截图失败，流程终止")
        return

    # 上传到 Gitee
    if gitee_owner and gitee_repo and gitee_token:
        delete_all_gitee_images(gitee_owner, gitee_repo, gitee_token)
        image_url = upload_to_gitee(image_path, gitee_owner, gitee_repo, gitee_token)
        
        if image_url and dingtalk_webhook and dingtalk_secret:
            send_image_to_dingtalk(dingtalk_webhook, dingtalk_secret, image_url)
        elif not image_url:
            print("图片上传失败，跳过钉钉通知")
        else:
            print("钉钉配置不完整，跳过钉钉通知")
    else:
        print("Gitee 配置不完整，跳过图片上传")
    
    print("=== 截图任务执行完成 ===")


if __name__ == "__main__":
    main()