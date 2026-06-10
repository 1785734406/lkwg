#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 GitHub API 手动触发 Merchant Screenshot 工作流"""

import os
import requests

def trigger_workflow(github_token, repo_owner="1785734406", repo_name="lkwg", workflow_name="merchant-screenshot.yml", ref="master"):
    """
    通过 GitHub API 触发工作流
    
    :param github_token: GitHub Personal Access Token（需要 repo 权限）
    :param repo_owner: 仓库所有者
    :param repo_name: 仓库名称
    :param workflow_name: 工作流文件名
    :param ref: 分支名称
    :return: 触发结果
    """
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows/{workflow_name}/dispatches"
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    data = {
        "ref": ref
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        if response.status_code == 204:
            print("✅ 工作流触发成功！")
            print(f"📋 工作流: {workflow_name}")
            print(f"🔀 分支: {ref}")
            print(f"🔗 查看运行状态: https://github.com/{repo_owner}/{repo_name}/actions/workflows/{workflow_name}")
            return True
        else:
            print(f"❌ 触发失败: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return False

if __name__ == "__main__":
    # 从环境变量获取 GitHub Token
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    
    if not GITHUB_TOKEN:
        print("❌ 请设置环境变量 GITHUB_TOKEN")
        print("💡 获取方式: https://github.com/settings/tokens (需要 repo 权限)")
        exit(1)
    
    # 触发工作流
    trigger_workflow(GITHUB_TOKEN)
