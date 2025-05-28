# 基于菜单的登录系统

由 Vincent-lg 贡献于 2016 年，Griatch 于 2019 年为现代 EvMenu 重新制作。

此系统将 Evennia 的登录过程更改为通过一系列问题询问账户名和密码，而不是要求一次性输入。这是通过 Evennia 的菜单系统 `EvMenu` 实现的。

## 安装

要安装此系统，请在 `mygame/server/conf/settings.py` 中添加以下内容：

```python
CMDSET_UNLOGGEDIN = "evennia.contrib.base_systems.menu_login.UnloggedinCmdSet"
CONNECTION_SCREEN_MODULE = "evennia.contrib.base_systems.menu_login.connection_screens"
```

重新加载服务器并重新连接以查看更改。

## 注意事项

如果您想修改连接屏幕的外观，可以将 `CONNECTION_SCREEN_MODULE` 指向您自己的模块。可以参考默认设置（另见 Evennia 文档）。


----

<small>此文档页面并非由 `evennia/contrib/base_systems/menu_login/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
