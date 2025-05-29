# 非交互式设置

第一次运行 `evennia start`（刚创建完数据库后），系统会要求你交互式地输入超级用户的用户名、电子邮件和密码。如果你是将 Evennia 部署为自动构建脚本的一部分，你可能不希望手动输入这些信息。

你可以通过向构建脚本传递环境变量来自动创建超级用户：

- `EVENNIA_SUPERUSER_USERNAME`
- `EVENNIA_SUPERUSER_PASSWORD`
- `EVENNIA_SUPERUSER_EMAIL` 是可选的。如果没有提供，将使用空字符串。

这些环境变量仅在_第一次_服务器启动时使用，然后将被忽略。例如：

```
EVENNIA_SUPERUSER_USERNAME=myname EVENNIA_SUPERUSER_PASSWORD=mypwd evennia start
```
