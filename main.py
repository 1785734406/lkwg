#!/usr/bin/env python3
# 主入口文件，调用 yxsr.py 的主函数

import os
import subprocess
import sys

def find_chromium_path():
    """查找系统级 Chromium 路径"""
    possible_paths = [
        '/usr/bin/chromium-browser',
        '/usr/bin/chromium',
        '/usr/local/bin/chromium',
        '/usr/lib/chromium-browser/chromium-browser'
    ]
    for path in possible_paths:
        if os.path.exists(path):
            print(f"找到 Chromium: {path}")
            return path
    return None

# 设置环境变量
chromium_path = find_chromium_path()
if chromium_path:
    os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = chromium_path
    print(f"设置环境变量 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH={chromium_path}")
else:
    print("警告：未找到系统级 Chromium")

import yxsr

if __name__ == "__main__":
    # 调用截图函数
    result = yxsr.screenshot_merchant_hd()
    if result:
        print(f"截图成功: {result}")
        # 发送到钉钉机器人
        yxsr.send_image_to_dingtalk(result)
    else:
        print("截图失败")