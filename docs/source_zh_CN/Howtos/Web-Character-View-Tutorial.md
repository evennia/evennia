# 网络角色视图教程

**在进行本教程之前，您可能想先阅读[更改网页教程](./Web-Changing-Webpage.md)中的介绍。**

在本教程中，我们将创建一个网页，用于显示游戏角色的统计信息。为此，以及我们希望制作的所有其他特定于游戏的页面，我们需要创建自己的 Django 应用程序。我们将把应用程序命名为 `character`，因为它将处理角色信息。从您的游戏目录中运行以下命令：

```bash
evennia startapp character
```

这将在 `mygame` 中创建一个名为 `character` 的新目录。为了保持整洁，让我们将其移动到 `web/` 子目录中。

```bash
mv character web  # (linux/mac)
move character web # (windows)
```

我们将其放在 `web/` 中以保持整洁，但您可以将其放在您喜欢的任何位置。它包含 Django 应用程序所需的所有基本文件。

请注意，我们不会编辑此新目录中的所有文件，许多生成的文件超出了本教程的范围。

为了让 Django 找到我们的新 Web 应用程序，我们需要将其添加到 `INSTALLED_APPS` 设置中。Evennia 的默认安装应用程序已经设置，因此在 `server/conf/settings.py` 中，我们只需扩展它们：

```python
INSTALLED_APPS += ('web.character',)
```

> 注意：末尾的逗号很重要。它确保 Python 将添加项解释为元组，而不是字符串。

我们首先需要创建一个 *视图* 和一个 *URL 模式* 来指向该视图。视图是生成访问者想要查看的网页的函数，而 URL 模式则让 Django 知道哪个 URL 应该触发该视图。该模式也可能提供一些自己的信息，正如我们将看到的那样。

这是我们的 `character/urls.py` 文件（**注意**：如果未为您生成空白文件，您可能需要创建此文件）：

```python
# URL patterns for the character app

from django.urls import path
from web.character.views import sheet

urlpatterns = [
    path("sheet/<int:object_id>", sheet, name="sheet")
]
```

此文件包含应用程序的所有 URL 模式。`urlpatterns` 列表中的 `url` 函数有三个参数。第一个参数是一个模式字符串，用于识别哪些 URL 是有效的。模式以 *正则表达式* 形式指定。正则表达式用于匹配字符串，并以一种特殊的、非常紧凑的语法编写。关于正则表达式的详细描述超出了本教程的范围，但您可以在[这里](https://docs.python.org/2/howto/regex.html)了解更多。目前，只需接受这个正则表达式要求访问者的 URL 看起来像这样：

```
sheet/123/
```

即 `sheet/` 后跟一个数字，而不是其他可能的 URL 模式。我们将把这个数字解释为对象 ID。由于正则表达式的格式，模式识别器将该数字存储在名为 `object_id` 的变量中。这个变量将传递给视图（见下文）。我们在第二个参数中添加导入的视图函数（`sheet`）。我们还添加了 `name` 关键字以识别 URL 模式本身。您应该始终为 URL 模式命名，这样在使用 `{% url %}` 标签在 HTML 模板中引用时会很方便（但我们将在本教程中不进一步讨论）。

> 安全注意：通常，用户无法看到游戏中的对象 ID（仅限超级用户）。公开游戏的对象 ID 使公众能够执行所谓的 [账户枚举攻击](http://www.sans.edu/research/security-laboratory/article/attacks-browsing)，以试图劫持您的超级用户账户。考虑这一点：在每个 Evennia 安装中，我们可以 *始终* 期望存在两个对象，并且具有相同的对象 ID—— Limbo (#2) 和您在开始时创建的超级用户 (#1)。因此，破坏者仅通过导航到 `sheet/1` 就可以获得劫持管理员账户所需信息的 50%。

接下来，我们创建 `views.py`，即 `urls.py` 引用的视图文件。

```python
# Views for our character app

from django.http import Http404
from django.shortcuts import render
from django.conf import settings

from evennia.utils.search import object_search
from evennia.utils.utils import inherits_from

def sheet(request, object_id):
    object_id = '#' + str(object_id)
    try:
        character = object_search(object_id)[0]
    except IndexError:
        raise Http404("I couldn't find a character with that ID.")
    if not inherits_from(character, settings.BASE_CHARACTER_TYPECLASS):
        raise Http404("I couldn't find a character with that ID. "
                      "Found something else instead.")
    return render(request, 'character/sheet.html', {'character': character})
```

正如前面所解释的，`urls.py` 中的 URL 模式解析器解析 URL 并将 `object_id` 传递给我们的视图函数 `sheet`。我们使用这个数字对对象进行数据库搜索。我们还确保这样的对象存在，并且它实际上是一个角色。视图函数还会传递一个 `request` 对象。这为我们提供了关于请求的信息，例如是否有登录用户在查看它——尽管我们在这里不会使用该信息，但记住这一点是很好的。

在最后一行中，我们调用 `render` 函数。除了 `request` 对象，`render` 函数接受一个 HTML 模板的路径和一个字典，您希望将额外数据传递给该模板。作为额外数据，我们传递了刚找到的角色对象。在模板中，它将作为变量 "character" 可用。

HTML 模板被创建为 `templates/character/sheet.html`，应放在您的 `character` 应用程序文件夹下。您可能需要手动创建 `template` 及其子文件夹 `character`。以下是要创建的模板：

```html
{% extends "base.html" %}
{% block content %}

    <h1>{{ character.name }}</h1>

    <p>{{ character.db.desc }}</p>

    <h2>Stats</h2>
    <table>
      <thead>
        <tr>
          <th>Stat</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Strength</td>
          <td>{{ character.db.str }}</td>
        </tr>
        <tr>
          <td>Intelligence</td>
          <td>{{ character.db.int }}</td>
        </tr>
        <tr>
          <td>Speed</td>
          <td>{{ character.db.spd }}</td>
        </tr>
      </tbody>
    </table>

    <h2>Skills</h2>
    <ul>
      {% for skill in character.db.skills %}
        <li>{{ skill }}</li>
      {% empty %}
        <li>This character has no skills yet.</li>
      {% endfor %}
    </ul>

    {% if character.db.approved %}
      <p class="success">This character has been approved!</p>
    {% else %}
      <p class="warning">This character has not yet been approved!</p>
    {% endif %}
{% endblock %}
```

在 Django 模板中，`{% ... %}` 表示 Django 理解的特殊 "函数"。`{{ ... }}` 块充当 "插槽"。它们会被代码块内部返回的任何值替换。

第一行 `{% extends "base.html" %}` 告诉 Django 此模板扩展了 Evennia 使用的基础模板。基础模板由主题提供。Evennia 附带了开源的第三方主题 `prosimii`。您可以在 `evennia/web/templates/prosimii` 中找到它及其 `base.html` 文件。像其他模板一样，这些模板可以被覆盖。

接下来的行是 `{% block content %}`。`base.html` 文件具有 `block`，这是模板可以扩展的占位符。主要的块（也是我们使用的）被命名为 `content`。

在模板中，我们可以在任何地方访问 `character` 变量，因为我们在 `views.py` 的 `render` 调用中传递了它。 这意味着我们同样可以访问角色的 `db` 属性，就像在普通的 Python 代码中一样。您无法在模板中调用带参数的函数——实际上，如果您需要执行任何复杂的逻辑，应该在 `views.py` 中进行，然后将结果作为更多变量传递给模板。但您仍然在展示数据时有相当大的灵活性。

我们也可以在这里进行一些小逻辑。我们使用 `{% for %} ... {% endfor %}` 和 `{% if %} ... {% else %} ... {% endif %}` 结构来更改模板的渲染方式，具体取决于用户的技能数量，或者用户是否获得批准（假设您的游戏有一个审批系统）。

最后，我们需要编辑的文件是主 URL 文件。这是为了将来自您新 `character` 应用程序的 URLs 平滑集成到 Evennia 的现有页面的 URLs 中。找到文件 `web/website/urls.py` 并更新其 `patterns` 列表如下：

```python
# web/website/urls.py

urlpatterns = [
    # ...
    path("character/", include('web.character.urls'))
]
```

现在，通过运行 `evennia reload` 重新加载服务器，并在浏览器中访问该页面。如果您没有更改默认设置，您应该能够在 `http://localhost:4001/character/sheet/1/` 找到角色 `#1` 的详情。

尝试在游戏中更新统计数据，并在浏览器中刷新页面。结果应该立即显示。

作为可选的最后一步，您还可以更改角色类型类，使其拥有一个名为 `get_absolute_url` 的方法。

```python
# typeclasses/characters.py

# 在 Character 内部
def get_absolute_url(self):
    from django.urls import reverse
    return reverse('character:sheet', kwargs={'object_id': self.id})
```

这样将在 Django 管理对象更改页面的右上角给您一个“在网站上查看”按钮，该按钮链接到您的新角色表单，并允许您通过在任何具有给定对象的模板中使用 `{{ object.get_absolute_url }}` 来获取角色页面的链接。

*现在您已经使用 Django 创建了一个基本页面和应用程序，您可能希望阅读完整的 Django 教程，以更好地了解它的功能。[您可以在这里找到 Django 的教程](https://docs.djangoproject.com/en/4.1/intro/tutorial01/).*
