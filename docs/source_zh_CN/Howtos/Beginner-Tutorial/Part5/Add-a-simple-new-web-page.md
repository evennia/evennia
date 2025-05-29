# 添加简单新网页
Evennia 利用 [Django](https://docs.djangoproject.com)，这是一个Web开发框架。
大型专业网站都是用 Django 制作的，且有大量的文档（和书籍）可供参考。
我们鼓励你至少看看 Django 的基础教程。在这里，我们将简单介绍一下它的工作原理，以帮助你入门。

我们假设你已安装并设置好了 Evennia。默认情况下，Evennia 安装包中自带了一个 Web 服务器和网站。你可以通过将网页浏览器指向 `http://localhost:4001` 来查看默认网站。你将看到一个包含一些游戏统计信息和 Evennia Web 客户端链接的通用欢迎页面。

在本教程中，我们将添加一个新页面，你可以在 `http://localhost:4001/story` 访问它。

### 创建视图

Django 的“视图”是一个普通的 Python 函数，Django 调用它来渲染你将在网页浏览器中看到的 HTML 页面。Django 可以利用视图函数对页面进行各种酷炫的操作，例如添加动态内容或即时更改页面，不过在这里，我们将简单地返回原始 HTML。

打开 `mygame/web/website` 文件夹，并在其中创建一个名为 `story.py` 的新模块文件。（如果你想保持整洁，也可以把它放在自己的文件夹中，但如果这样做，请不要忘记在新文件夹中添加一个空的 `__init__.py` 文件。添加 `__init__.py` 文件告诉 Python 可以从新文件夹中导入模块。对于本教程，你的新 `story.py` 模块的示例内容应如下所示：

```python
# 在 mygame/web/website/story.py 中

from django.shortcuts import render

def storypage(request):
    return render(request, "story.html")
```

上述视图利用了 Django 提供的一个快捷方式：_render_。渲染快捷方式从请求中提供模板信息。例如，它可以提供游戏名称，并进行渲染。

### HTML 页面

接下来，我们需要找到 Evennia（和 Django）查找 HTML 文件的位置，这些文件在 Django 的术语中被称为 *模板*。你可以在设置中指定这些位置（有关更多信息，请参见 `default_settings.py` 中的 `TEMPLATES` 变量），但在这里我们将使用现有的位置。

导航到 `mygame/web/templates/website/`，并在其中创建一个名为 `story.html` 的新文件。由于这不是 HTML 教程，因此该文件的内容将很简单：

```html
{% extends "base.html" %}
{% block content %}
<div class="row">
  <div class="col">
    <h1>关于一棵树的故事</h1>
    <p>
        这是一个关于一棵树的故事，一个经典的故事……
    </p>
  </div>
</div>
{% endblock %}
```

如上所示，Django 使我们能够轻松扩展我们的基本样式，因为我们使用了 _render_ 快捷方式。如果你希望不利用 Evennia 的基本样式，你可以选择这样做：

```html
<html>
  <body>
    <h1>关于一棵树的故事</h1>
    <p>
    这是一个关于一棵树的故事，一个经典的故事……
    </p>
  </body>
</html>
```

### URL

当你在网页浏览器中输入地址 `http://localhost:4001/story` 时，Django 将解析端口后的内容 - 在这里是 `/story` - 以便找出你希望显示的页面。Django 如何知道 `/story` 应该链接到哪个 HTML 文件呢？你需要在 `mygame/web/website/urls.py` 文件中告诉 Django 这些地址模式对应的文件。现在在编辑器中打开它。

Django 在此文件中查找变量 `urlpatterns`。你需要将新的 `story` 模式和相应的路径添加到 `urlpatterns` 列表中，然后再将其与默认的 `urlpatterns` 合并。它的样子可以如下所示：

```python
"""
此处重新路由从一个 URL 到一个 Python 视图函数/类。
主要的 web/urls.py 包含所有 URL（URL 根）的这些路由，
以便可以重定向到所有网站页面。
"""
from django.urls import path

from web.website import story

from evennia.web.website.urls import urlpatterns as evennia_website_urlpatterns

# 在这里添加模式
urlpatterns = [
    # path("url-pattern", imported_python_view),
    path(r"story", story.storypage, name="Story"),
]

# 被 Django 读取
urlpatterns = urlpatterns + evennia_website_urlpatterns
```

上述代码从我们早前创建的 `mygame/web/website/` 中导入了我们的 `story.py` Python 视图模块，并添加了相应的 `path` 实例。`path` 的第一个参数是我们希望查找的 URL 模式（`"story"`）作为正则表达式，然后是我们希望调用的来自 `story.py` 的视图函数。

就这样。重新加载 Evennia - `evennia reload` - 你现在应该能够在浏览器中访问 `http://localhost:4001/story`，并查看你的新故事页面是如何通过 Python 渲染的！
