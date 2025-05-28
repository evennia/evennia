# 网络角色生成

## 介绍

本教程将创建一个简单的基于 Web 的界面，用于生成新的游戏内角色。账户需要首先使用其 `AccountDB` 账户登录网站。完成角色生成后，角色会立即被创建，账户可以立即登录游戏并玩耍（角色不需要工作人员的批准或其他操作）。本指南不涉及如何在网站上创建具有正确权限以转移到其网页创建的角色的 AccountDB。

建议将 `AUTO_CREATE_CHARACTER_WITH_ACCOUNT = False` 设置为 `False`，以便所有玩家角色都可以通过此方式创建。

您应该对 Django 的模型模板视图框架有一定的了解。您需要理解基本的 [Web 角色视图教程](./Web-Character-View-Tutorial.md) 中正在发生的事情。如果您不理解所列的教程或对 Django 的基础知识没有掌握，请查看 [Django 教程](https://docs.djangoproject.com/en/4.1/intro/)，以了解 Django 的基本功能，然后再将 Evennia 纳入其中（Evennia 与网站接口共享其 API 和属性）。本指南将概述所需的模型、视图、URLs 和 HTML 模板的格式。

## 图片

以下是我们将要制作的简单应用程序的一些屏幕截图。

索引页面，尚未进行角色申请：

***
![索引页面，尚未进行角色申请。](https://lh3.googleusercontent.com/-57KuSWHXQ_M/VWcULN152tI/AAAAAAAAEZg/kINTmVlHf6M/w425-h189-no/webchargen_index2.gif)
***

单击“创建”链接后，您可以生成角色（我们这里只会有名称和背景，您可以根据游戏的需要添加任何内容）：

***
![角色创建。](https://lh3.googleusercontent.com/-ORiOEM2R_yQ/VWcUKgy84rI/AAAAAAAAEZY/B3CBh3FHii4/w607-h60-no/webchargen_creation.gif)
***

回到索引页面。输入我们的角色申请后（我们将角色命名为“TestApp”），您会看到它被列出：

***
![输入申请后。](https://lh6.googleusercontent.com/-HlxvkvAimj4/VWcUKjFxEiI/AAAAAAAAEZo/gLppebr05JI/w321-h194-no/webchargen_index1.gif)
***

我们还可以通过单击它来查看已编写的角色申请 - 这将带我们到 *详细信息* 页面：

***
![角色申请的详细视图。](https://lh6.googleusercontent.com/-2m1UhSE7s_k/VWcUKfLRfII/AAAAAAAAEZc/UFmBOqVya4k/w267-h175-no/webchargen_detail.gif)
***

## 安装应用程序

假设您的游戏名为“mygame”，请导航到您的 `mygame/` 目录，并输入：

```bash
cd web
evennia startapp chargen
```

这将在 `mygame/web/` 中初始化一个名为“chargen”的新 Django 应用程序。我们将其放在 `web/` 下以便将所有 Web 内容放在一起，但您可以根据自己的喜好进行组织。这是一个包含 Django 需要的一些基本启动内容的目录。

接下来，导航到 `mygame/server/conf/settings.py`，添加或修改以下行，以使 Evennia（和 Django）知道我们的新应用程序：

```python
INSTALLED_APPS += ('web.chargen',)
```

之后，我们将定义我们的 *模型*（数据库存储的描述）、*视图*（服务器端网站内容生成器）、*URLs*（Web 浏览器如何找到页面）和 *模板*（网页的结构）。

### 安装 - 检查点：

* 您应该在 `mygame/web/` 目录中有一个名为 `chargen` 的文件夹或您选择的名称。
* 您应该在 `settings.py` 中将应用程序名称添加到 `INSTALLED_APPS`。

## 创建模型

模型在 `mygame/web/chargen/models.py` 中创建。

[Django 数据库模型](../Concepts/Models.md) 是描述您想要管理的数据在数据库中的存储方式的 Python 类。您选择存储的任何数据都存储在与游戏相同的数据库中，您可以在此访问所有游戏对象。

我们需要定义角色申请的实际内容。这将因游戏而异，因此在本教程中，我们将定义一个简单的角色表单，包含以下数据库字段：

* `app_id` (AutoField): 该角色申请表的主键。
* `char_name` (CharField): 新角色的名称。
* `date_applied` (DateTimeField): 接收该申请的日期。
* `background` (TextField): 角色故事背景。
* `account_id` (IntegerField): 此申请所属的账户 ID。这是来自 AccountDB 对象的 AccountID。
* `submitted` (BooleanField): 根据申请是否已提交显示 `True`/`False`。

> 注意：在一个完善的游戏中，您可能希望他们能够选择种族、技能、属性等。

我们的 `models.py` 文件应如下所示：

```python
# in mygame/web/chargen/models.py

from django.db import models

class CharApp(models.Model):
    app_id = models.AutoField(primary_key=True)
    char_name = models.CharField(max_length=80, verbose_name='角色名称')
    date_applied = models.DateTimeField(verbose_name='申请日期')
    background = models.TextField(verbose_name='背景')
    account_id = models.IntegerField(default=1, verbose_name='账户 ID')
    submitted = models.BooleanField(default=False)
```

您应该考虑将您的申请与账户链接的方式。在本教程中，我们使用角色申请模型上的 `account_id` 属性，以便跟踪哪些角色属于哪个账户。由于账户 ID 是 Evennia 的主键，因此它是一个很好的候选者，因为您在 Evennia 中永远不会有两个相同的 ID。您可以自由使用其他任何内容，但在本指南中，我们将使用账户 ID 将角色申请与正确的账户连接。

### 模型 - 检查点：

* 您应该已经用上面的模型类填充了 `mygame/web/chargen/models.py`（最终添加与您游戏所需匹配的字段）。

## 创建视图

*视图* 是服务器端构造，用于使动态数据可用于网页。我们将它们添加到 `mygame/web/chargen/views.py` 中。我们的示例中的每个视图代表特定网页的骨架。我们将在这里使用三种视图和三个页面：

* 索引（管理 `index.html`）。这是您导航到 `http://yoursite.com/chargen` 时看到的内容。
* 详细显示表单（管理 `detail.html`）。显示给定角色的统计信息的页面。
* 角色创建表单（管理 `create.html`）。主要表单，包含需要填写的字段。

### *索引* 视图

让我们先从索引开始。

我们希望角色能够看到他们创建的角色，因此我们将这样做：

```python
# file mygame/web/chargen/views.py

from django.shortcuts import render
from .models import CharApp

def index(request):
    current_user = request.user  # 当前登录用户
    p_id = current_user.id  # 账户 ID
    # 此账户提交的角色
    sub_apps = CharApp.objects.filter(account_id=p_id, submitted=True)
    context = {'sub_apps': sub_apps}
    # 使 'context' 中的变量可用于网页模板
    return render(request, 'chargen/index.html', context)
```

### *详细信息* 视图

我们的详细信息页面将显示用户可以看到的相关角色申请信息。由于这是一个基本示例，我们的详细信息页面将仅显示两个字段：

* 角色名称
* 角色背景

我们将再次使用账户 ID 仅仅是为了确认尝试查看角色页面的人确实是拥有该申请的账户。

```python
# file mygame/web/chargen/views.py

def detail(request, app_id):
    app = CharApp.objects.get(app_id=app_id)
    name = app.char_name
    background = app.background
    submitted = app.submitted
    p_id = request.user.id
    context = {'name': name, 'background': background,
               'p_id': p_id, 'submitted': submitted}
    return render(request, 'chargen/detail.html', context)
```

### *创建* 视图

可预见的是，我们的 *创建* 函数将是视图中最复杂的，因为它需要接受来自用户的信息，验证这些信息，并将该信息发送到服务器。验证表单内容后，我们将实际创建一个可玩的角色。

我们将首先定义表单。在我们的简单示例中，我们只需要角色的名称和背景。此表单在 `mygame/web/chargen/forms.py` 中创建：

```python
# file mygame/web/chargen/forms.py

from django import forms

class AppForm(forms.Form):
    name = forms.CharField(label='角色名称', max_length=80)
    background = forms.CharField(label='背景')
```

现在我们在视图中使用此表单。

```python
# file mygame/web/chargen/views.py

from web.chargen.models import CharApp
from web.chargen.forms import AppForm
from django.http import HttpResponseRedirect
from datetime import datetime
from evennia.objects.models import ObjectDB
from django.conf import settings
from evennia.utils import create

def creating(request):
    user = request.user
    if request.method == 'POST':
        form = AppForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            background = form.cleaned_data['background']
            applied_date = datetime.now()
            submitted = True
            if 'save' in request.POST:
                submitted = False
            app = CharApp(char_name=name, background=background,
                          date_applied=applied_date, account_id=user.id,
                          submitted=submitted)
            app.save()
            if submitted:
                # 创建实际的角色对象
                typeclass = settings.BASE_CHARACTER_TYPECLASS
                home = ObjectDB.objects.get_id(settings.GUEST_HOME)
                # 将权限处理程序转换为字符串
                perms = str(user.permissions)
                # 创建角色
                char = create.create_object(typeclass=typeclass, key=name,
                                             home=home, permissions=perms)
                user.add_character(char)
                # 添加适当的锁，以便账户可以操控该角色
                char.locks.add(" or ".join([
                    f"puppet:id({char.id})",
                    f"pid({user.id})",
                    "perm(Developers)",
                    "pperm(Developers)",
                ]))
                char.db.background = background  # 设置角色背景
            return HttpResponseRedirect('/chargen')
    else:
        form = AppForm()
    return render(request, 'chargen/create.html', {'form': form})
```

> 请注意，我们基本上是使用 Evennia API 创建角色，并从 `AccountDB` 对象获取相应的权限并将其复制到角色对象中。我们将用户权限属性提取并将该字符串列表转换为字符串对象，以便 `create_object` 函数能够正确处理权限。

最重要的是，在创建的角色对象上必须设置以下属性：

* Evennia [权限](../Components/Permissions.md)（从 `AccountDB` 复制）。
* 正确的 `puppet` [锁](../Components/Locks.md)，以便账户实际上可以作为该角色进行操作。
* 相关的角色 [类型类](../Components/Typeclasses.md)。
* 角色名称（关键）。
* 角色的家园位置（默认值为 `#2`）。

其他属性在严格意义上是可选的，例如角色的 `background` 属性。将此功能分解并在您的账户拥有的角色对象上创建一个单独的 _create_character 函数可能是一个好主意。但是使用 Evennia API，设置自定义属性和在您 Evennia 游戏目录内的主要内容中设置它是一样容易的。

完成所有这些后，我们的 `views.py` 文件应如下所示：

```python
# file mygame/web/chargen/views.py

from django.shortcuts import render
from web.chargen.models import CharApp
from web.chargen.forms import AppForm
from django.http import HttpResponseRedirect
from datetime import datetime
from evennia.objects.models import ObjectDB
from django.conf import settings
from evennia.utils import create

def index(request):
    current_user = request.user  # 当前登录用户
    p_id = current_user.id  # 账户 ID
    # 此账户提交的角色
    sub_apps = CharApp.objects.filter(account_id=p_id, submitted=True)
    context = {'sub_apps': sub_apps}
    return render(request, 'chargen/index.html', context)

def detail(request, app_id):
    app = CharApp.objects.get(app_id=app_id)
    name = app.char_name
    background = app.background
    submitted = app.submitted
    p_id = request.user.id
    context = {'name': name, 'background': background,
               'p_id': p_id, 'submitted': submitted}
    return render(request, 'chargen/detail.html', context)

def creating(request):
    user = request.user
    if request.method == 'POST':
        form = AppForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            background = form.cleaned_data['background']
            applied_date = datetime.now()
            submitted = True
            if 'save' in request.POST:
                submitted = False
            app = CharApp(char_name=name, background=background,
                          date_applied=applied_date, account_id=user.id,
                          submitted=submitted)
            app.save()
            if submitted:
                # 创建实际的角色对象
                typeclass = settings.BASE_CHARACTER_TYPECLASS
                home = ObjectDB.objects.get_id(settings.GUEST_HOME)
                # 将权限处理程序转换为字符串
                perms = str(user.permissions)
                # 创建角色
                char = create.create_object(typeclass=typeclass, key=name,
                                             home=home, permissions=perms)
                user.add_character(char)
                # 添加适当的锁，以便账户可以操控该角色
                char.locks.add(" or ".join([
                    f"puppet:id({char.id})",
                    f"pid({user.id})",
                    "perm(Developers)",
                    "pperm(Developers)",
                ]))
                char.db.background = background  # 设置角色背景
            return HttpResponseRedirect('/chargen')
    else:
        form = AppForm()
    return render(request, 'chargen/create.html', {'form': form})
```

### 创建视图 - 检查点：

* 您已经定义了一个具有索引、详细信息和创建函数的 `views.py`。
* 您已经定义了一个带有 `AppForm` 类的 `forms.py`，这是 `views.py` 中的 `creating` 函数所需要的。
* 您的 `mygame/web/chargen` 目录现在应包含 `views.py` 和 `forms.py` 文件。

## 创建 URLs

URL 模式有助于将请求从 Web 浏览器重定向到正确的视图。这些模式在 `mygame/web/chargen/urls.py` 中创建。

```python
# file mygame/web/chargen/urls.py

from django.urls import path
from web.chargen import views

urlpatterns = [
    # url: /chargen/
    path("", views.index, name='chargen-index'),
    # url: /chargen/5/
    path("<int:app_id>/", views.detail, name="chargen-detail"),
    # url: /chargen/create
    path("create/", views.creating, name='chargen-creating'),
]
```

您可以根据需要更改格式。为了使其更安全，您可以从“详细”URL 中移除 app_id，而是仅使用一个统一的字段，例如 account_id，来查找用于显示的所有角色申请对象。

要将其添加到我们的网页中，我们还必须更新主 `mygame/website/urls.py` 文件；这将帮助将我们的新 chargen 应用程序与其余网站连接起来。您可以将 `urlpatterns` 变量更改为包含：

```python
# in file mygame/website/urls.py

from django.urls import path, include

urlpatterns = [
    # 在 /chargen URL 下使所有 chargen 端点可用
    path("chargen/", include("web.chargen.urls")),
]
```

### URLs - 检查点：

* 您已经在 `mygame/web/chargen` 目录中创建了 `urls.py` 文件。
* 您已经编辑了主 `mygame/web/urls.py` 文件，以将 URLs 添加到 `chargen` 目录中。

## HTML 模板

所以我们已经定义了 URL 模式、视图和模型。现在我们必须定义用户实际看到和交互的 HTML 模板。本教程中，我们使用的是 Evennia 附带的基本 *prosimii* 模板。

请注意，我们使用 `user.is_authenticated` 确保用户在未登录的情况下无法创建角色。

这些文件将全部放入 `/mygame/web/chargen/templates/chargen/` 目录中。

### index.html

此 HTML 模板应包含当前账户所有活动申请的列表。出于演示目的，我们将仅列出账户已提交的申请。您可以轻松调整此内容以包含已保存的申请或其他类型的申请（如果您有不同类型的申请）。

请回顾 `views.py` 以查看我们定义这些模板所使用的变量。

```html
<!-- file mygame/web/chargen/templates/chargen/index.html -->

{% extends "base.html" %}
{% block content %}
{% if user.is_authenticated %}
    <h1>角色生成</h1>
    {% if sub_apps %}
        <ul>
        {% for sub_app in sub_apps %}
            <li><a href="/chargen/{{ sub_app.app_id }}/">{{ sub_app.char_name }}</a></li>
        {% endfor %}
        </ul>
    {% else %}
        <p>您尚未提交任何角色申请。</p>
    {% endif %}
  {% else %}
    <p>请先 <a href="{% url 'login'%}">登录</a>。</p>
{% endif %}
{% endblock %}
```

### detail.html

此页面应显示其申请的详细角色信息。这将仅显示其名称和角色背景。您可能希望扩展此内容，以显示更多字段以适应您的游戏。在完善的角色生成中，您可能希望扩展 submitted 布尔属性，以允许账户保存角色申请并稍后提交。

```html
<!-- file mygame/web/chargen/templates/chargen/detail.html -->

{% extends "base.html" %}
{% block content %}
<h1>角色信息</h1>
{% if user.is_authenticated %}
    {% if user.id == p_id %}
        <h2>{{name}}</h2>
        <h2>背景</h2>
        <p>{{background}}</p>
        <p>已提交: {{submitted}}</p>
    {% else %}
        <p>您没有提交此角色。</p>
    {% endif %}
{% else %}
<p>您尚未登录。</p>
{% endif %}
{% endblock %}
```

### create.html

我们的创建 HTML 模板将使用我们在 `views.py/forms.py` 中定义的 Django 表单来驱动大多数应用程序流程。每个字段都有一个表单输入，正是我们在 `forms.py` 中定义的，这很好。我们使用 POST 作为方法，因为我们正在向服务器发送将更新数据库的信息。相对而言，使用 GET 会安全性差得多。您可以阅读网络上的其他文档了解 GET 与 POST 之间的区别。

```html
<!-- file mygame/web/chargen/templates/chargen/create.html -->

{% extends "base.html" %}
{% block content %}
<h1>角色创建</h1>
{% if user.is_authenticated %}
<form action="/chargen/create/" method="post">
    {% csrf_token %}
    {{ form }}
    <input type="submit" name="submit" value="提交"/>
</form>
{% else %}
<p>您尚未登录。</p>
{% endif %}
{% endblock %}
```

### 模板 - 检查点：

* 在您的 `mygame/web/chargen/templates/chargen` 目录中创建 `index.html`、`detail.html` 和 `create.html` 模板。

## 激活您的新角色生成

完成本教程后，您应该已编辑或创建以下文件：

```bash
mygame/web/website/urls.py
mygame/web/chargen/models.py
mygame/web/chargen/views.py
mygame/web/chargen/urls.py
mygame/web/chargen/templates/chargen/index.html
mygame/web/chargen/templates/chargen/create.html
mygame/web/chargen/templates/chargen/detail.html
```

完成所有这些文件后，请在 `mygame/` 文件夹中运行：

```bash
evennia makemigrations
evennia migrate
```

这将创建和更新模型。如果此阶段出现任何错误，请仔细阅读回溯，应该相对容易找出错误所在。

登录网站（您需要事先注册一个玩家账户才能做到这一点）。接下来，您导航到 `http://yourwebsite.com/chargen`（如果在本地运行，它将是 `http://localhost:4001/chargen`），您将看到您的新应用程序在运行。

这应该为您 figuring out 角色生成提供一个良好的起点。主要的困难在于设置您新创建的角色对象的适当设置。幸运的是，Evennia API 使这变得简单。

## 在角色生成中添加无验证码的 reCAPTCHA

很遗憾，如果您的服务器向 Web 开放，机器人可能会来访问并利用您的开放表单创建成百上千的角色，如果您给了他们这种机会。本节将向您展示如何使用 [No CAPTCHA reCAPTCHA](https://www.google.com/recaptcha/intro/invisible.html)，这是 Google 设计的。不仅使用方便，对人类用户也很友好…… 只需简单的复选框，如果 Google 更加怀疑，则可能会出现更困难的测试，通常包含一张图像和常规文本。值得注意的是，只要 Google 不怀疑您是机器人，这实际上对普通用户和屏幕阅读器用户都非常有用，因为在图像中阅读是相当困难的，不可能的。此外，将其添加到您的网站也很简单。

### 第 1 步：从 Google 获取站点密钥和秘密密钥

第一步是向 Google 请求一种安全地验证网站与其服务的方法。为此，我们需要创建一个站点密钥和一个秘密密钥。前往 [https://www.google.com/recaptcha/admin](https://www.google.com/recaptcha/admin) 创建站点密钥。只要您拥有 Google 帐户，这非常简单。

创建站点密钥后，请安全保存。还要复制您的秘密密钥。您应该在网页上找到这两种信息。两者都将包含许多字母和数字。

### 第 2 步：安装和配置专用 Django 应用程序

由于 Evennia 运行在 Django 上，添加我们的 CAPCHA 和执行适当检查的最简单方法是安装专用的 Django 应用程序。非常简单：

```bash
pip install django-nocaptcha-recaptcha
```

并将其添加到您的设置中。在 `mygame/server/conf/settings.py` 中，您可能会有如下内容：

```python
# ...
INSTALLED_APPS += (
    'web.chargen',
    'nocaptcha_recaptcha',
)
```

暂时不要关闭设置文件。我们还需要将站点密钥和秘密密钥添加进去。您可以在下面添加它们：

```python
# NoReCAPCHA 站点密钥
NORECAPTCHA_SITE_KEY = "在此处粘贴您的站点密钥"
# NoReCAPCHA 秘密密钥
NORECAPTCHA_SECRET_KEY = "在此处放置您的秘密密钥"
```

### 第 3 步：将 CAPCHA 添加到我们的表单中

最后，我们需要将 CAPCHA 添加到我们的表单中。这也非常简单。首先，打开您的 `web/chargen/forms.py` 文件。我们将添加一个新字段，但希望所有的麻烦都已经为我们解决。根据您的需要进行更新，您最终可能会得到如下内容：

```python
from django import forms
from nocaptcha_recaptcha.fields import NoReCaptchaField

class AppForm(forms.Form):
    name = forms.CharField(label='角色名称', max_length=80)
    background = forms.CharField(label='背景')
    captcha = NoReCaptchaField()
```

正如您所见，我们添加了一行导入（第 2 行）和我们表单中的一个字段。

最后，我们需要更新我们的 HTML 文件以添加 Google 库。您可以打开 `web/chargen/templates/chargen/create.html`。只需添加一行：

```html
<script src="https://www.google.com/recaptcha/api.js" async defer></script>
```

您应该将其放在页面底部。在关闭 body 之前放置它是最好的，但在此期间，基础页面没有提供 footer 块，因此我们将其放在内容块中。请注意，这不是最佳位置，但可以工作。最后，您的 `web/chargen/templates/chargen/create.html` 文件应如下所示：

```html
{% extends "base.html" %}
{% block content %}
<h1>角色创建</h1>
{% if user.is_authenticated %}
<form action="/chargen/create/" method="post">
    {% csrf_token %}
    {{ form }}
    <input type="submit" name="submit" value="提交"/>
</form>
{% else %}
<p>您尚未登录。</p>
{% endif %}
<script src="https://www.google.com/recaptcha/api.js" async defer></script>
{% endblock %}
```

重新加载并打开 [http://localhost:4001/chargen/create](http://localhost:4001/chargen/create/)，您应该能看到您美丽的 CAPCHA，紧挨着“提交”按钮。尽量不勾选复选框，以查看会发生什么。并在勾选复选框的情况下执行相同的操作！
