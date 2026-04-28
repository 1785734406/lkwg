# GitHub Actions 配置说明

## 概述

此项目使用 GitHub Actions 实现定时自动截图远行商人页面并发送到钉钉。

## GitHub Secrets 配置

在 GitHub 仓库的 Settings → Secrets and variables → Actions 中配置以下环境变量：

### 必需的环境变量

| Secret 名称 | 描述 | 示例值 |
|------------|------|--------|
| `DINGTALK_WEBHOOK` | 钉钉机器人 Webhook URL | `https://oapi.dingtalk.com/robot/send?access_token=xxx` |
| `DINGTALK_SECRET` | 钉钉机器人签名密钥 | `SECxxx` |
| `GITEE_OWNER` | Gitee 仓库所有者用户名 | `your_username` |
| `GITEE_REPO` | Gitee 仓库名称 | `your_repo_name` |
| `GITEE_TOKEN` | Gitee 个人访问令牌 | `gitee_token_here` |

### 可选的环境变量

| Secret 名称 | 描述 | 默认值 |
|------------|------|--------|
| `LKWG_URL` | 远行商人页面 URL | `https://www.onebiji.com/hykb_tools/comm/lkwgmerchant/preview.php?id=1&immgj=0&imm=1` |

## 如何获取配置信息

### 钉钉机器人配置
1. 在钉钉群中创建自定义机器人
2. 设置安全方式为"加签"
3. 复制 Webhook URL 和 Secret

### Gitee 配置
1. 登录 Gitee，进入个人设置
2. 找到"私人令牌"，创建新的令牌
3. 勾选 `projects` 权限
4. 复制生成的令牌

## 定时任务配置

当前配置为每天运行4次（UTC时间）：
- 00:00（北京时间 08:00）
- 04:00（北京时间 12:00）
- 08:00（北京时间 16:00）
- 12:00（北京时间 20:00）

如需修改定时，编辑 `.github/workflows/merchant-screenshot.yml` 中的 `cron` 表达式。

## 手动触发

在 GitHub Actions 页面，可以手动触发 workflow：
1. 进入仓库的 Actions 标签页
2. 选择 "Merchant Screenshot" workflow
3. 点击 "Run workflow" 按钮

## 文件说明

- `yxsr.py` - 原始脚本（包含硬编码配置）
- `yxsr_ci.py` - CI 专用脚本（使用环境变量）
- `requirements.txt` - Python 依赖包列表
- `.github/workflows/merchant-screenshot.yml` - GitHub Actions 配置

## 注意事项

1. 确保所有 secrets 都已正确配置
2. Gitee 仓库需要提前创建好 `images` 文件夹
3. 首次运行可能需要较长时间下载 Playwright 浏览器
4. 脚本执行后会删除 Gitee 和本地的所有相关图片