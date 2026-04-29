---
name: "erp-login"
description: "通过 chrome-cli 脚本登录 ERP 后台。当需要登录 ERP 后台或访问 web-2.xyzlerp.com 网址时调用该技能。"
---

# ERP 后台登录技能

该技能提供自动化操作流程，使用 `chrome-cli.py` 脚本完成 ERP 后台的登录任务。

## 账号密码
- 用户名：`U001`
- 密码：`xyGit2077!@#`



## 工作流程

当你需要执行登录操作时，请严格按照以下步骤调用脚本：

### 1. 访问登录页面
首先打开指定的 ERP 页面网址。
```bash
# 执行 open 命令访问 ERP 登录页面
python {workspace}/skills/xunyue-cli/chrome-cli.py open --url http://web-2.xyzlerp.com/#/inventory/finish-return-tern
```
*提示：执行后需从控制台输出中获取 `页面唯一标识符ID` (如 `0-0`)，并根据输出的 HTML 结构找到账号、密码输入框和登录按钮的 XPath。*

### 2. 填写账号
获取到输入框 XPath 和页面 ID 后，填写账号。
```bash
# 执行 fill 命令向账号输入框填写用户名
python {workspace}/skills/xunyue-cli/chrome-cli.py fill --id <页面ID> --xpath "<账号输入框XPath>" --value "<用户名>"
```

### 3. 填写密码
向密码输入框填写相应的密码。
```bash
# 执行 fill 命令向密码输入框填写密码
python {workspace}/skills/xunyue-cli/chrome-cli.py --id <页面ID> --xpath "<密码输入框XPath>" --value "<密码>"
```

### 4. 点击登录
点击登录按钮以完成登录操作。
```bash
# 执行 touch 命令点击登录按钮
python {workspace}/skills/xunyue-cli/chrome-cli.py touch --id <页面ID> --xpath "<登录按钮XPath>"
```

## 注意事项
- 在执行上述任何操作前，请确保本地浏览器已在调试模式下启动。
- 每一步执行完毕后需验证输出，确保执行无误后再进入下一步。