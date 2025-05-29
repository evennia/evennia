# 基于电子邮件的登录系统

贡献者：Griatch, 2012

这是一个登录系统的变体，它要求用户输入电子邮件地址而不是用户名进行登录。请注意，它不验证电子邮件，只使用其作为标识符，而不是用户名。

这曾是 Evennia 的默认登录方式，后来被更标准的用户名 + 密码系统替代（需提供电子邮件出于某种原因导致用户在扩展时产生了很多困惑。电子邮件在内部并不是严格需要的，也没有发送确认电子邮件）。

## 安装

在您的设置文件中添加/编辑以下行：

```python
CMDSET_UNLOGGEDIN = "contrib.base_systems.email_login.UnloggedinCmdSet"
CONNECTION_SCREEN_MODULE = "contrib.base_systems.email_login.connection_screens"
```

就是这样。重新加载服务器并重新连接以查看效果。

## 注意事项

如果您想修改连接屏幕的外观，请将 `CONNECTION_SCREEN_MODULE` 指向您自己的模块。使用默认设置作为指南（另见 Evennia 文档）。
