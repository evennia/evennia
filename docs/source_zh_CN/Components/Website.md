# 游戏网站

当 Evennia 启动时，它会作为 [Server](./Portal-And-Server.md) 进程的一部分启动一个 [Web 服务器](./Webserver.md)。这个服务器使用 [Django](https://docs.djangoproject.com) 来展示一个简单但功能齐全的默认游戏网站。在默认设置下，打开浏览器访问 [localhost:4001](http://localhost:4001) 或 [127.0.0.1:4001](http://127.0.0.1:4001) 即可查看。

网站允许现有玩家使用他们之前注册游戏时使用的账户名和密码登录。如果用户通过 [Web 客户端](./Webclient.md) 登录，他们也会自动登录到网站，反之亦然。因此，如果你已登录网站，打开 Web 客户端将自动以该账户登录游戏。

默认网站显示一个“欢迎！”页面，并提供一些有用资源的链接。它还显示当前连接的玩家数量等统计信息。

在顶部菜单中，你可以找到：
- **主页** - 返回首页。
- **文档** - 链接到最新的 Evennia 稳定文档。
- **角色** - 这是将游戏内角色连接到网站的演示。它将显示所有 _typeclasses.characters.Character_ 类型类实体的列表，并允许你查看它们的描述和可选图像。列表仅对登录用户可见。
- **频道** - 这是将游戏内聊天连接到网站的演示。它将显示所有可用频道的列表，并允许你查看最新讨论。大多数频道需要登录，但 `Public` 频道也可以被未登录用户查看。
- **帮助** - 这将游戏内的 [帮助系统](./Help-System.md) 连接到网站。所有公开可用或你的账户可访问的数据库帮助条目都可以阅读。这是为人们提供游戏外阅读帮助的好方法。
- **在线游戏** - 在浏览器中打开 [Web 客户端](./Webclient.md)。
- **管理** - 只有在登录时才会显示 [Web 管理](Web admin)。
- **登录/注销** - 允许你使用游戏中相同的凭据进行身份验证。
- **注册** - 允许你注册一个新账户。这与首次登录游戏时创建新账户相同。

## 修改默认网站

你可以从游戏目录中修改和覆盖网站的所有方面。你主要会在设置文件中进行操作（`mygame/server/conf/settings.py`），以及在游戏目录的 `web` 文件夹中（如果你的游戏文件夹是 `mygame/`，则为 `mygame/web/`）。

> 在测试你的修改时，最好在设置文件中添加 `DEBUG = True`。这将使你在浏览器中直接看到详细的回溯信息，而不是通用的 404 或 500 错误页面。请记住，DEBUG 模式会泄漏内存（用于保留调试信息），因此在生产游戏中使用是不安全的！

如 [Web 服务器](./Webserver.md) 页面所述，获取网页的过程如下：

1. Web 浏览器向服务器发送带有 URL 的 HTTP 请求。
2. `urls.py` 使用正则表达式将该 URL 匹配到一个 _视图_（一个 Python 函数或可调用类）。
3. 加载并执行正确的 Python 视图。
4. 视图拉入一个 _模板_，这是一个带有占位符标记的 HTML 文档，并根据需要填充这些标记（它也可能使用 _表单_ 以相同方式自定义用户输入）。一个 HTML 页面也可能指向静态资源（通常是 CSS，有时是图像等）。
5. 渲染的 HTML 页面作为 HTTP 响应返回给浏览器。如果 HTML 页面需要静态资源，浏览器将单独获取这些资源，然后显示给用户。

如果你查看 [evennia/web/](github:evennia/web) 目录，你会发现以下结构（省略了与网站无关的内容）：

```
  evennia/web/
    ...
    static/
        website/
            css/
               (css 样式文件)
            images/
               (要显示的图像)

    templates/
        website/
          (html 文件)

    website/
      urls.py
      views/
        (与网站相关的 python 文件)

    urls.py
```

顶级 `web/urls.py` 文件“包含”了 `web/website/urls.py` 文件——这样所有与网站相关的 URL 处理都集中在一个地方。

这是与网站相关的 `mygame/web/` 文件夹的布局：

```
  mygame/web/
    ...
    static/
      website/
        css/
        images/

    templates/
      website/

      website/
        urls.py
        views/

    urls.py
```

```{versionchanged} 1.0

  使用旧版本 Evennia 创建的游戏文件夹将缺少大部分方便的 `mygame/web/` 布局。如果你使用的是旧版本的游戏目录，应从中复制缺少的 `evennia/game_template/web/` 文件夹，以及主 `urls.py` 文件。

```

如你所见，`mygame/web/` 文件夹是 `evennia/web/` 文件夹结构的副本，只是 `mygame` 文件夹大多是空的。

对于静态文件和模板文件，Evennia 会首先在 `mygame/static` 和 `mygame/templates` 中查找，然后才去 `evennia/web/` 的默认位置。因此，要覆盖这些资源，你只需在 `mygame/web/` 下的正确位置放置一个同名文件（然后重新加载服务器）。最简单的方法通常是复制原始文件并进行修改。

覆盖的视图（Python 模块）还需要对 `website/urls.py` 文件进行额外调整——你必须确保将 URL 指向新版本，而不是使用原始版本。

## 常见网页更改示例

```{important}

  Django 是一个非常成熟的 Web 设计框架。网上有无数的教程、课程和书籍可以解释如何使用 Django。因此，这些示例仅作为入门指南。

```

### 更改标题和简介

网站的标题和简介可以通过调整 `settings.SERVERNAME` 和 `settings.GAME_SLOGAN` 来更改。你的设置文件位于 `mygame/server/conf/settings.py`，只需设置/添加：

```python
SERVERNAME = "My Awesome Game"
GAME_SLOGAN = "The best game in the world"
```

### 更改 Logo

Evennia 的大眼蛇 Logo 可能不是你想要的游戏 Logo。模板会查找文件 `web/static/website/images/evennia_logo.png`。只需将你自己的 PNG Logo（64x64 像素）放在那里，并命名相同即可。

### 更改首页 HTML

网站的首页通常在 HTML 术语中称为“索引”。

首页模板位于 `evennia/web/templates/website/index.html`。只需将其复制到 `mygame/web/` 的相应位置。在那里修改并重新加载服务器以查看更改。

Django 模板有一些特殊功能，使其与普通 HTML 文档不同——它们包含一个特殊的模板语言，用 `{% ... %}` 和 `{{ ... }}` 标记。

一些重要的事情：

- `{% extends "base.html" %}` - 这相当于 Python 中的 `from othermodule import *` 语句，但用于模板。它允许给定模板使用导入（扩展）模板中的所有内容，但也可以覆盖任何想要更改的内容。这使得所有页面看起来相同变得容易，并避免了大量的样板代码。
- `{% block blockname %}...{% endblock %}` - 块是可继承的命名代码片段，可以在一个地方修改，然后在其他地方使用。这有点像反向继承，因为通常 `base.html` 定义一个空块，比如 `contents`：`{% block contents %}{% endblock %}`，但确保将其放在正确的位置，比如在主正文旁边的侧边栏等。然后每个页面都 `{% extends "base.html %"}` 并制作自己的 `{% block contents} <actual content> {% endblock %}`。它们的 `contents` 块现在将覆盖 `base.html` 中的空块，并出现在文档的正确位置，而无需扩展模板指定其周围的所有其他内容！
- `{{ ... }}` 是通常嵌入在 HTML 标签或内容中的“插槽”。它们引用一个 _上下文_（基本上是一个字典），Python _视图_ 将其提供给模板。上下文的键通过点符号访问，因此如果你向模板提供一个上下文 `{"stats": {"hp": 10, "mp": 5}}`，你可以通过 `{{ stats.hp }}` 访问它，以在该位置显示 `10`。

这允许模板继承（使所有页面看起来相同而无需重复编写相同的内容）。

在 [Django 模板语言文档](https://docs.djangoproject.com/en/4.1/ref/templates/language/)中可以找到更多信息。

### 更改网页颜色和样式

你可以调整整个网站的 [CSS](https://en.wikipedia.org/wiki/Cascading_Style_Sheets)。如果你查看 `evennia/web/templates/website/base.html` 文件，你会发现我们使用了 [Bootstrap 4](https://getbootstrap.com/docs/4.6/getting-started/introduction/) 工具包。

许多结构性 HTML 功能实际上来自 Bootstrap，因此你通常可以只在 HTML 文件中的元素上添加 Bootstrap CSS 类，以获得各种效果，如文本居中或类似效果。

网站的自定义 CSS 位于 `evennia/web/static/website/css/website.css`，但我们也在同一位置查找一个（目前为空的）`custom.css`。你可以覆盖任一文件，但如果你只在 `custom.css` 中添加内容，可能更容易恢复你的更改。

将要修改的 CSS 文件复制到 `mygame/web` 中的相应位置。修改它并重新加载服务器以查看更改。

你也可以在不重新加载的情况下应用静态文件，但可以在终端中运行以下命令：

```bash
evennia collectstatic --no-input
```

（重新加载服务器时会自动运行此命令）。

> 请注意，在看到新 CSS 文件应用之前，你可能需要在不使用缓存的情况下刷新浏览器（例如，在 Firefox 中按 Ctrl-F5）。

例如，将 `custom.css` 添加/复制到 `mygame/web/static/website/css/` 并添加以下内容：

```css
.navbar {
  background-color: #7a3d54;
}

.footer {
  background-color: #7a3d54;
}
```

重新加载后，你的网站现在有一个红色主题！

> 提示：学习使用你的 Web 浏览器的 [开发者工具](https://torquemag.io/2020/06/browser-developer-tools-tutorial/)。
> 这些工具允许你“实时”调整 CSS，以找到你喜欢的外观，并仅在你想永久更改时将其复制到 .css 文件中。

### 更改首页功能

逻辑都在视图中。要查找索引页面视图的位置，我们查看 `evennia/web/website/urls.py`。在这里，我们找到以下行：

```python
# 在 evennia/web/website/urls.py 中

  ...
  # 网站首页
  path("", index.EvenniaIndexView.as_view(), name="index"),
  ...
```

第一个 `""` 是空 URL - 根目录 - 你只需输入 `localhost:4001/` 而没有额外路径时得到的内容。正如预期的那样，这会导致索引页面。通过查看导入，我们发现视图位于 `evennia/web/website/views/index.py` 中。

将此文件复制到 `mygame/web` 中的相应位置。然后调整你的 `mygame/web/website/urls.py` 文件以指向新文件：

```python
# 在 mygame/web/website/urls.py 中

# ...

from web.website.views import index

urlpatterns = [
    path("", index.EvenniaIndexView.as_view(), name="index")

]
# ...
```

因此，我们只需从新位置导入 `index` 并指向它。重新加载后，首页将重定向以使用你的副本而不是原始版本。

首页视图是一个类 `EvenniaIndexView`。这是一个 [Django 类视图](https://docs.djangoproject.com/en/4.1/topics/class-based-views/)。与函数相比，类视图中发生的事情不太明显（因为类实现了许多功能作为方法），但它功能强大且更容易扩展/修改。

类属性 `template_name` 设置了在 `templates/` 文件夹下使用的模板的位置。因此，`website/index.html` 指向 `web/templates/website/index.html`（正如我们在上面已经探索过的那样）。

`get_context_data` 是一个方便的方法，用于为模板提供上下文。在索引页面的情况下，我们希望获得游戏统计信息（最近玩家数量等）。然后，这些信息可用于在模板中使用 `{{ ... }}` 插槽，如上一节所述。

### 更改其他网站页面

其他子页面的处理方式相同 - 将模板或静态资源复制到正确的位置，或复制视图并将 `website/urls.py` 指向你的副本。只需记得重新加载。

## 添加新网页

### 使用平面页面

添加新网页的最简单方法是使用 [Web 管理](./Web-Admin.md) 中可用的 `Flat Pages` 应用。该页面将与网站的其他部分具有相同的样式。

要使用 `Flat Pages` 模块，你必须首先设置一个 _站点_（或域）以使用。你只需执行一次此操作。

- 转到 Web 管理并选择 `Sites`。如果你的游戏在 `mygreatgame.com`，那就是你需要添加的域。对于本地实验，添加域 `localhost:4001`。注意域的 `id`（当你点击新域时查看 URL，例如，如果是 `http://localhost:4001/admin/sites/site/2/change/`，则 id 为 `2`）。
- 现在将行 `SITE_ID = <id>` 添加到你的设置文件中。

接下来，你可以轻松创建新页面。

- 转到 `Flat Pages` Web 管理并选择添加新平面页面。
- 设置 URL。如果你希望页面显示为例如 `localhost:4001/test/`，则在此处添加 `/test/`。你需要添加前导和尾随斜杠。
- 将 `Title` 设置为页面的名称。
- `Content` 是页面主体的 HTML 内容。尽情发挥吧！
- 最后选择你之前创建的 `Site`，并保存。
- （在高级部分，你可以设置必须登录才能查看页面等）。

你现在可以访问 `localhost:4001/test/` 并查看你的新页面！

### 添加自定义新页面

`Flat Pages` 页面不允许（或很少）动态内容和自定义。为此，你需要自己添加所需的组件。

让我们看看如何从头开始创建一个 `/test/` 页面。

- 在 `mygame/web/templates/website/` 下添加一个新的 `test.html` 文件。最简单的方法是基于现有文件。确保 `{% extend base.html %}` 以获得与网站其他部分相同的样式。
- 在 `mygame/web/website/views/` 下添加一个新的视图 `testview.py`（不要命名为 `test.py`，否则 Django/Evennia 会认为它包含单元测试）。在其中添加一个视图以处理你的页面。这是一个用于开始的最小视图（在 [Django 文档](https://docs.djangoproject.com/en/4.1/topics/class-based-views/)中阅读更多内容）：

    ```python
    # mygame/web/website/views/testview.py

    from django.views.generic import TemplateView

    class MyTestView(TemplateView):
        template_name = "website/test.html"
    ```

- 最后，从 `mygame/web/website/urls.py` 指向你的视图：

    ```python
    # 在 mygame/web/website/urls.py 中

    # ...
    from web.website.views import testview

    urlpatterns = [
        # ...
        # 我们可以在这里省略初始的 /
        path("test/", testview.MyTestView.as_view())
    ]
    ```

- 重新加载服务器，你的新页面就可用了。你现在可以通过视图和模板继续添加各种高级动态内容！

## 用户表单

到目前为止创建的所有页面都涉及向用户 _展示_ 信息。用户也可以通过 _表单_ 在页面上 _输入_ 数据。一个示例是一个字段和滑块的页面，你填写以创建一个角色，底部有一个大的“提交”按钮。

首先，这必须在 HTML 中表示。`<form> ... </form>` 是你需要添加到模板的标准 HTML 元素。它还有一些其他要求，例如 `<input>` 和通常的 JavaScript 组件（但通常 Django 会帮助完成这些）。如果你不熟悉 HTML 表单的工作原理，[在此处阅读相关内容](https://docs.djangoproject.com/en/4.1/topics/forms/#html-forms)。

其基本要点是，当你点击“提交”表单时，将向服务器发送一个包含用户输入数据的 POST HTML 请求。现在由服务器确保数据合理（验证），然后以某种方式处理输入（如创建新角色）。

在后端，我们需要指定验证和处理表单数据的逻辑。这是通过 `Form` [Django 类](https://docs.djangoproject.com/en/4.1/topics/forms/#forms-in-django)完成的。它在自身上指定 _字段_，定义如何验证该数据。

然后通过在视图类中添加 `form_class = MyFormClass` 将表单链接到视图（在 `template_name` 旁边）。

在 `evennia/web/website/forms.py` 中有几个示例表单。阅读 [在 Django 中构建表单](https://docs.djangoproject.com/en/4.1/topics/forms/#building-a-form-in-django)也是个好主意——它涵盖了你所需的一切。
