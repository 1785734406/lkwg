#!/usr/bin/env python3
# 主入口文件，调用 yxsr.py 的主函数

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