# 在您的网站上添加Wiki

```{warning}
截至 2023 年，[django wiki](https://django-wiki.readthedocs.io/en/main/) 仅支持 Django 4.0。而 Evennia 需要 Django 4.1 以上版本。目前 django-wiki 仍在维护，并希望将来进行更新，但现在可能会有一些安装问题。本教程可能无法直接使用。
```

```{note}
在进行本教程之前，您可能想先阅读 [基本网页教程](./Web-Changing-Webpage.md) 中的介绍。此外，阅读 [Django 教程](https://docs.djangoproject.com/en/4.1/intro/tutorial01/) 的前三部分也可能会有所帮助。
```

本教程将提供分步安装Wiki的过程。幸运的是，您不必手动创建这些功能，因为其他人已经实现了这一点，我们可以很容易地与 Django 集成。我决定专注于 [Django-wiki](https://django-wiki.readthedocs.io/)。

[Django-wiki](https://django-wiki.readthedocs.io/) 提供了与Wiki相关的众多功能，目前活跃维护（至少到现在为止），并且在 Evennia 中安装也不算太难。您可以在 [这里查看 Django-wiki 的演示](https://demo.django-wiki.org)。

## 基本安装

您应该首先关闭正在运行的 Evennia 服务器。我们将运行迁移，并稍微调整虚拟环境。打开终端并激活您用于运行 `evennia` 命令的 Python 环境。

如果您使用了 Evennia 安装说明中的默认位置，它应该是以下之一：

* 在 Linux 上：
    ```
    source evenv/bin/activate
    ```
* 或在 Windows 上：
    ```
    evenv\bin\activate
    ```

### 使用 pip 安装

使用 pip 安装Wiki：

```
pip install wiki
```

这可能需要一些时间，因为 Django-wiki 有一些依赖项。

### 在设置中添加Wiki

您需要添加一些设置以在网站上运行Wiki应用程序。打开您的 `server/conf/settings.py` 文件，并在底部添加以下内容（但在导入 `secret_settings` 之前）。以下是添加了 Django-wiki 的设置文件示例：

```python
# 使用 Evennia 的默认设置，除非显式覆盖
from evennia.settings_default import *

######################################################################
# Evennia 基础服务器配置
######################################################################

# 这是您游戏的名称，请确保吸引人！
SERVERNAME = "demowiki"

######################################################################
# Django-wiki 设置
######################################################################
INSTALLED_APPS += (
    'django.contrib.humanize.apps.HumanizeConfig',
    'django_nyt.apps.DjangoNytConfig',
    'mptt',
    'sorl.thumbnail',
    'wiki.apps.WikiConfig',
    'wiki.plugins.attachments.apps.AttachmentsConfig',
    'wiki.plugins.notifications.apps.NotificationsConfig',
    'wiki.plugins.images.apps.ImagesConfig',
    'wiki.plugins.macros.apps.MacrosConfig',
)

# 禁用Wiki处理登录/注册，以使用您的 Evennia 登录系统
WIKI_ACCOUNT_HANDLING = False
WIKI_ACCOUNT_SIGNUP_ALLOWED = False

# 启用Wiki链接，例如 [[Getting Started]]
WIKI_MARKDOWN_KWARGS = {
    'extensions': [
        'wikilinks',
    ]
}

######################################################################
# 在 secret_settings.py 中给出的设置会覆盖此文件中的设置。
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("找不到 secret_settings.py 文件或导入失败。")
```

在“Django-wiki 设置”部分中的所有内容都是您需要包含的。

### 添加新的 URL

接下来，您需要将两个 URL 添加到 `web/urls.py` 文件中。通过修改 `urlpatterns` 来使其看起来像这样：

```python
# 添加模式
urlpatterns = [
    # 网站
    path("", include("web.website.urls")),
    # Web 客户端
    path("webclient/", include("web.webclient.urls")),
    # Web 管理
    path("admin/", include("web.admin.urls")),
    # Wiki
    path("wiki/", include("wiki.urls")),
    path("notifications/", include("django_nyt.urls")),
]
```

最后两行是您需要添加的内容。

### 运行迁移

接下来，您需要运行迁移，因为Wiki应用程序会添加一些表到我们的数据库中：

```
evennia migrate
```

### 初始化Wiki

最后一步！请再次启动您的服务器。

```
evennia start
```

完成启动后，访问您的 Evennia 网站（例如 http://localhost:4001），使用超级用户账户登录（如果您还没有登录）。然后，访问您的新Wiki（例如 http://localhost:4001/wiki）。它会提示您创建一个起始页面 - 输入您想要的内容，您可以稍后更改。

恭喜！您完成了所有设置！

## 定义Wiki权限

Wiki通常被视为一种协作努力——但您可能仍想设定一些规则，关于谁可以做什么。谁可以创建新文章？编辑它们？删除它们？等等。

实现这一点的两种最简单的方法是使用 Django-wiki 的基于组的权限系统，或者，由于这是一个 Evennia 网站，您可以在设置文件中定义与 Evennia 的权限系统相关的自定义权限规则。

### 组权限

Wiki本身控制每篇文章的读取/编辑权限。文章的创建者将始终对该文章拥有读/写权限。此外，文章将具有基于组的权限和通用权限。

默认情况下，Evennia 的权限组不会被Wiki识别，因此您需要自己创建。请访问您游戏的 Django 管理面板中的组页面，并在此处添加您希望为Wiki设置的权限组。

***注意：*** *如果您希望将这些组与您游戏的权限级别连接，您需要修改游戏，使两者都适用于账户。*

添加完这些组后，它们将立即可在您的Wiki中使用！

### 设置权限

Django-wiki 还允许您通过设置文件中的站点范围权限规则来绕过其基于文章的权限。如果您不想使用组系统，或者如果您想要一种将 Evennia 权限级别与Wiki访问简单连接的解决方案，这就是您要走的路。

以下是您可以放入 `settings.py` 文件的基本设置示例：

```python
# 在 server/conf/settings.py 中
# ...

# 自定义方法将Wiki权限链接到游戏权限
def is_superuser(article, user):
    """如果用户是超级用户则返回 True，否则返回 False。"""
    return not user.is_anonymous and user.is_superuser

def is_builder(article, user):
    """如果用户是构建者则返回 True，否则返回 False。"""
    return not user.is_anonymous and user.permissions.check("Builder")

def is_player(article, user):
    """如果用户是玩家则返回 True，否则返回 False。"""
    return not user.is_anonymous and user.permissions.check("Player")

# 创建新用户
WIKI_CAN_ADMIN = is_superuser

# 更改文章的所有者和组
WIKI_CAN_ASSIGN = is_superuser

# 更改文章的组，即使名字不变
WIKI_CAN_ASSIGN_OWNER = is_superuser

# 更改文章的读/写权限
WIKI_CAN_CHANGE_PERMISSIONS = is_superuser

# 标记文章为已删除
WIKI_CAN_DELETE = is_builder

# 锁定或永久删除文章
WIKI_CAN_MODERATE = is_superuser

# 创建或编辑任何页面
WIKI_CAN_WRITE = is_builder

# 阅读任何页面
WIKI_CAN_READ = is_player

# 完全禁止未登录用户编辑和创建文章
WIKI_ANONYMOUS_WRITE = False
```

权限函数可以根据访问用户的任何信息进行检查，只要函数返回 True（允许）或 False（不允许）。

有关可能的设置的完整列表，您可以查看 [django-wiki 文档](https://django-wiki.readthedocs.io/en/latest/settings.html)。
