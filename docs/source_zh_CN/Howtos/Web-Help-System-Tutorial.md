# Web帮助系统教程

**在进行此教程之前，您可能希望阅读 [Changing the Web page tutorial](./Web-Changing-Webpage.md) 中的介绍。** 阅读 [Django tutorial](https://docs.djangoproject.com/en/4.0/intro/tutorial01/) 的前三个部分可能也会有所帮助。

本教程将向您展示如何通过网站访问帮助系统。根据登录的用户或匿名角色，帮助命令和常规帮助条目都将可见。

本教程将向您展示如何：

- 创建一个新的页面以添加到您的网站。
- 利用基本视图和基本模板。
- 在您的网站上访问帮助系统。
- 确定此页面的查看者是否已登录，以及如果已登录，属于哪一个帐户。

## 创建我们的应用

第一步是创建新的 Django *应用*。在 Django 中，应用可以包含页面和机制：您的网站可能包含不同的应用。实际上，Evennia 提供的开箱即用的网站已经有三个应用：一个用于处理整个网页客户端的 "webclient" 应用，一个用于包含基本页面的 "website" 应用，以及一个由 Django 提供的用于创建简单管理界面的第三个应用。因此，我们将平行创建另一个应用，并给它一个清晰的名称，以代表我们的帮助系统。

从您的游戏目录中，使用以下命令：

```bash
cd web
evennia startapp help_system
```

这将在您的 `mygame/` 文件夹中创建一个新的 `help_system` 文件夹。为了保持整洁，我们将其移动到 `web/` 文件夹中：

```bash
mv help_system web  # (linux)
move help_system web  # (windows)
```

> 注意：将应用命名为 "help" 会更加明确，但这个名称已经被 Django 使用。

我们将新应用放在 `web/` 下以将所有与 web 相关的内容放在一起，但您可以根据自己的喜好进行组织。这里的结构看起来是这样的：

```
mygame/
    ...
    web/
        help_system/
        ...
```

"web/help_system" 目录包含 Django 创建的文件。我们将使用其中的一些文件，但如果您想了解更多关于它们的信息，您可以阅读 [Django tutorial](https://docs.djangoproject.com/en/4.1/intro/tutorial01/)。

最后，您需要做一件事：您的文件夹已经添加，但 Django 不知道它，Django 不知道它是一个新应用。我们需要告诉它，我们通过编辑一个简单的设置来实现。打开您的 "server/conf/settings.py" 文件，添加或编辑以下行：

```python
# Web configuration
INSTALLED_APPS += (
        "web.help_system",
)
```

您可以开始 Evennia，如果愿意，可以访问您的网站，可能是在 [http://localhost:4001](http://localhost:4001)。不过您不会看到任何不同的内容：我们添加了应用，但它非常空。

## 我们的新页面

此时，我们的新 *应用* 主要包含空文件，您可以进行探索。为了为帮助系统创建一个页面，我们需要添加：

- 一个 *视图*，处理我们页面的逻辑。
- 一个 *模板* 来显示我们的新页面。
- 一个指向我们页面的新 *URL*。

> 我们可以只创建一个视图和一个新 URL，但这不是推荐的工作方式。使用模板构建会更加方便。

### 创建视图

在 Django 中，*视图* 是放在应用的 `views.py` 文件中的简单 Python 函数。它将处理当用户通过输入 *URL* 请求此信息时触发的行为（*视图* 和 *URL* 之间的连接稍后会进行讨论）。

让我们创建我们的视图。您可以打开 `web/help_system/views.py` 文件并粘贴以下内容：

```python
from django.shortcuts import render

def index(request):
    """'index' 视图。"""
    return render(request, "help_system/index.html")
```

我们的视图处理所有代码逻辑。这次，逻辑不多：当调用这个函数时，它将渲染我们将要创建的模板。但这也是我们将在之后进行大部分工作的地方。

### 创建模板

在我们的 *视图* 中调用的 `render` 函数请求 *模板* `help_system/index.html`。我们应用的 *模板* 存储在应用目录的 "templates" 子目录中。Django 可能已经创建了 "templates" 文件夹。如果没有，请自行创建。在该文件夹中，再创建一个文件夹 "help_system"，然后在此文件夹中创建一个名为 "index.html" 的文件。哇，这层次有点复杂。您目录结构（从 `web` 开始）应该如下所示：

```
web/
    help_system/
        ...
        templates/
            help_system/
                index.html
```

打开 "index.html" 文件并粘贴以下内容：

```html
{% extends "base.html" %}
{% block titleblock %}Help index{% endblock %}
{% block content %}
<h2>Help index</h2>
{% endblock %}
```

以下是此模板逐行的小说明：

1. 它加载 "base.html" *模板*。它描述了所有页面的基本结构，顶部有菜单和底部的页脚，可能还有其他信息，如图像和每个页面上要显示的内容。您可以创建不继承 "base.html" 的模板，但您应该有充分的理由这样做。
2. "base.html" *模板* 定义了页面的所有结构。剩下的工作是重写我们页面的一些部分。这些部分被称为 *块*。在第 2 行，我们重写名为 "blocktitle" 的块，这部分包含页面的标题。
3. 这里同样，我们重写名为 "content" 的 *块*，它包含我们网页的主要内容。这个块比较大，因此我们在多行定义它。
4. 这是一段完全正常的 HTML 代码，用于显示二级标题。
5. 最后，我们关闭名为 "content" 的 *块*。

### 创建新的 URL

添加页面的最后一步是我们需要添加一个指向它的 *URL*……否则用户将无法访问它。我们应用的 URLs 存储在应用目录的 `urls.py` 文件中。

打开 `web/help_system/urls.py` 文件（您可能需要创建它），使它看起来如下：

```python
# help_system 应用的 URL 模式

from django.urls import path
from .views import index

urlpatterns = [
    path('', index)
]
```

`urlpatterns` 变量是 Django/Evennia 查找以确定如何将用户输入的 URL 定向到您编写的视图代码的内容。

最后我们需要将其绑定到您游戏的主命名空间中。编辑文件 `mygame/web/urls.py`。在其中，您会再次找到 `urlpatterns` 列表。添加一个新的 `path` 到列表的末尾。

```python
# mygame/web/urls.py
# [...]

# 添加模式
urlpatterns = [
    # 网站
    path("", include("web.website.urls")),
    # 网页客户端
    path("webclient/", include("web.webclient.urls")),
    # 网站管理
    path("admin/", include("web.admin.urls")),

    # 我们的帮助系统
    path('help/', include('web.help_system.urls'))   # <--- 新增
]

# [...]
```

当用户请求您网站上的特定 *URL* 时，Django 将：

1. 读取在 "web/urls.py" 中定义的自定义模式列表。这里有一个模式，告诉 Django 所有以 'help/' 开头的 URL 应该发送到 'help_system' 应用。'help/' 部分将被删除。
2. 然后 Django 将检查 "web.help_system/urls.py" 文件。它只包含一个 URL，即空的 (`^$`)。

换句话说，如果 URL 是 '/help/'，那么 Django 将执行我们定义的视图。

### 让我们看看它的工作

您现在可以重新加载或启动 Evennia。在浏览器中打开一个标签页，访问 [http://localhost:4001/help/](http://localhost:4001/help/)。如果一切顺利，您应该看到新页面……它并不空，因为 Evennia 使用了我们的 "base.html" *模板*。页面内容上只有一个标题，写着 "help index"。请注意，页面的标题是 "mygame - Help index"（"mygame" 由您游戏的名称替换）。

从现在开始，进行下一步并添加功能会更容易。

### 简要提醒

我们将尝试以下内容：

- 在线访问命令帮助和帮助条目。
- 根据用户是否登录拥有各种命令和帮助条目。

在页面方面，我们将会有：

- 一个显示帮助主题列表的页面。
- 一个显示帮助主题内容的页面。

第一个页面将链接到第二个页面。

> 我们应该创建两个 URL 吗？

答案是……也许。这取决于您想做什么。我们通过 "/help/" URL 访问我们的帮助索引。我们可以通过 "/help/desc"（查看 "desc" 命令的详细信息）访问帮助条目的详细信息。问题是我们的命令或帮助主题可能包含不应出现在 URL 中的特殊字符。解决此问题的不同方法有很多。我决定在这里使用 *GET 变量*，这将创建如下 URL：

```
/help?name=desc
```

如果您使用此系统，则不必添加新 URL：GET 和 POST 变量可以通过我们的请求访问，我们将很快看到。

## 处理已登录用户

我们的要求之一是让帮助系统根据我们的帐户进行定制。如果具有管理员访问权限的帐户登录，页面应该显示许多普通用户无法访问的命令。也许还有一些额外的帮助主题。

幸运的是，在我们的视图中获取已登录帐户非常简单（记住我们将在那里进行大多数编码）。传递给我们函数的 *request* 对象包含一个 `user` 属性。此属性始终存在：例如，我们无法测试它是否为 `None`。但是，当请求来自未登录的用户时，`user` 属性将包含一个匿名 Django 用户。然后我们可以使用 `is_anonymous` 方法来判断用户是否已登录。甚至如果用户已登录，`request.user` 还包含对帐户对象的引用，这将有助于我们将游戏和在线系统联系在一起。

因此，我们可能会得到类似这样的代码：

```python
def index(request):
    """'index' 视图。"""
    user = request.user
    if not user.is_anonymous() and user.character:
        character = user.character
```

> 注意：当您的 MULTISESSION_MODE 设置为 0 或 1 时，此代码有效。当设置为更高的值时，您会有如下代码：

```python
def index(request):
    """'index' 视图。"""
    user = request.user
    if not user.is_anonymous() and user.characters:
        character = user.characters[0]
```

在这种情况下，它将选择该帐户的第一个角色。

但如果用户未登录怎么办？同样，我们有不同的解决方案。最简单的方法之一是创建一个作为帮助系统的默认角色的角色。您可以通过游戏创建它：连接到它并输入：

```bash
@charcreate anonymous
```

系统应该回答：

```
创建新角色 anonymous。使用 @ic anonymous 作为此角色进入游戏。
```

因此，在我们的视图中，我们可以有这样的代码：

```python
from typeclasses.characters import Character

def index(request):
    """'index' 视图。"""
    user = request.user
    if not user.is_anonymous() and user.character:
        character = user.character
    else:
        character = Character.objects.get(db_key="anonymous")
```

这次，无论如何我们都有一个有效的角色：请记住，如果您处于多会话模式高于 1，请适当调整此代码。

## 完整系统

我们要做的是浏览所有命令和帮助条目，并列出该角色（无论是我们的 'anonymous' 角色，还是我们的已登录角色）可以看到的所有命令。

代码会稍微复杂一点，但总的来说，可以分成小块：

- `index` 函数是我们的视图：
    - 它开始时获取角色，如我们在前面的部分中看到的。
    - 它获取该角色可访问的帮助主题（命令和帮助条目）。这是另一个处理这部分的函数。
    - 如果我们的 URL 中有一个 *GET 变量* "name"（例如 "/help?name=drop"），它将检索该变量。如果这不是有效的主题名称，它返回一个 *404*。否则，它渲染名为 "detail.html" 的模板，以显示我们主题的详细信息。
    - 如果没有 *GET 变量* "name"，则渲染 "index.html" 来显示主题列表。
- `_get_topics` 是一个私有函数。它的唯一任务是检索角色可以执行的命令，以及该同一角色可以看到的帮助条目。此代码更具 Evennia 特定性，而非 Django 特定性，因此在本教程中不会详细讨论。只需注意，所有帮助主题都存储在字典中。这是为了简化我们在模板中显示它们的工作。

请注意，在我们请求渲染 *模板* 的两个情况下，我们都向 `render` 传递了第三个参数，即用于模板的变量字典。我们可以通过这种方式传递变量，我们将在模板中使用它们。

### 索引模板

让我们看一下完整的 "index" *模板*。您可以打开 "web/help_system/templates/help_system/index.html" 文件并将以下内容粘贴到其中：

```html
{% extends "base.html" %}
{% block titleblock %}Help index{% endblock %}
{% block content %}
<h2>Help index</h2>
{% if categories %}
    {% for category, topics in categories %}
        <h2>{{ category|capfirst }}</h2>
        <table>
        <tr>
        {% for topic in topics %}
            {% if forloop.counter|divisibleby:"5" %}
                </tr>
                <tr>
            {% endif %}
            <td><a href="{% url 'help_system:index' %}?name={{ topic.name|urlencode }}">
            {{ topic.name }}</td>
        {% endfor %}
        </tr>
        </table>
    {% endfor %}
{% endif %}
{% endblock %}
```

此模板的细节更多。它的作用是：

1. 遍历所有类别。
2. 对于所有类别，显示包含类别名称的二级标题。
3. 类别中的所有主题（记住，它们可以是命令或帮助条目）都显示在表格中。比较棘手的部分是，在循环超过 5 时，它将创建一个新行。每行最多有 5 列的表格。
4. 对于表格中的每个单元格，我们创建一个链接，重定向到详细页面（见下文）。URL 的格式类似于 "help?name=say"。我们使用 `urlencode` 确保特殊字符得到正确转义。

### 详细模板

现在是时候显示主题（命令或帮助条目）的详细信息了。您可以创建文件 "web/help_system/templates/help_system/detail.html"。您可以在其中粘贴以下代码：

```html
{% extends "base.html" %}
{% block titleblock %}Help for {{ topic.name }}{% endblock %}
{% block content %}
<h2>{{ topic.name|capfirst }} help topic</h2>
<p>Category: {{ topic.category|capfirst }}</p>
{{ topic.content|linebreaks }}
{% endblock %}
```

这个模板更容易阅读。可能有一些 *过滤器* 对您来说是未知的，但它们只是用于格式化。

### 将所有内容组合在一起

请记得重新加载或启动 Evennia，然后转到 [http://localhost:4001/help](http://localhost:4001/help/)。您应该看到所有角色可访问的命令和主题列表。尝试登录（单击您网站菜单中的 "login" 链接）并再次转到相同的页面。您现在应该看到更详细的命令和帮助条目列表。单击一个以查看其详细信息。

## 改进此功能

如往常一样，教程旨在帮助您感到舒适，以便您可以自己添加新功能和代码。以下是一些改进此小功能的想法：

- 在详细模板的底部添加一个链接返回索引可能会很有用。
- 在主菜单中链接到此页面的链接将是很好的……目前您必须输入 URL，用户不会猜到它。
- 此时，颜色没有被处理，这并不奇怪。但您可以添加它。
- 使帮助条目相互链接将并不简单，但会很不错。例如，如果您看到一个关于如何使用多个命令的帮助条目，最好这些命令本身是链接，以显示它们的详细信息。
