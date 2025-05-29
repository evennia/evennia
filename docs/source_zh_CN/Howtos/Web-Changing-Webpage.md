# 更改游戏网站

Evennia 使用 [Django](https://www.djangoproject.com/) Web 框架作为其数据库配置和提供的网站的基础。虽然要全面理解 Django 需要阅读 Django 文档，但我们提供了此教程以帮助您快速入门，并了解其与 Evennia 的相关性。本文详细介绍如何设置所有内容。 [基于 Web 的角色视图教程](./Web-Character-View-Tutorial.md) 提供了一个更明确的示例，用于制作与您的游戏连接的自定义网页，您可以在完成本指南后阅读。

## 基本概述

Django 是一个 Web 框架。它为快速轻松构建网站提供了一套开发工具。

Django 项目被分为多个 *应用*，这些应用共同为一个项目做贡献。例如，您可能有一个用于进行投票的应用，一个用于显示新闻帖子，或者像我们一样，用于创建 Web 客户端的应用。

每个应用都有一个 `urls.py` 文件，用于指定该应用使用的 [URL](https://en.wikipedia.org/wiki/Uniform_resource_locator)，一个 `views.py` 文件用于 URL 激活的代码，一个 `templates` 目录用于以 [HTML](https://en.wikipedia.org/wiki/Html) 显示代码的结果，还有一个 `static` 文件夹，用于存放资产，例如 [CSS](https://en.wikipedia.org/wiki/CSS)、[Javascript](https://en.wikipedia.org/wiki/Javascript) 和图像文件（您可能会注意到，您的 mygame/web 文件夹中没有 `static` 或 `templates` 文件夹。这是故意的，下面将进一步解释）。Django 应用程序还可能包含一个 `models.py` 文件，用于在数据库中存储信息。我们在这里不改变任何模型，想了解更多，请查看 [新模型](../Concepts/Models.md) 页面（以及 [Django 文档](https://docs.djangoproject.com/en/4.1/topics/db/models/)）。

还有一个根 `urls.py`，确定整个项目的 URL 结构。默认游戏模板中包含了一个入门级 `urls.py`，并自动导入了 Evennia 的所有默认 URL。这个文件位于 `web/urls.py` 中。

## 更改首页的logo

Evennia 的默认 logo 是一个可爱的转动的蛇绕着齿轮的地球。虽然它很可爱，但可能无法代表您的游戏。因此，您可能希望首先更换一个自己的 logo。

Django Web 应用程序都有 _静态资产_：CSS 文件、Javascript 文件和图像文件。为了确保最终项目拥有所需的所有静态文件，系统会收集来自每个应用的 `static` 文件夹中的文件，并将其放置在 `settings.py` 中定义的 `STATIC_ROOT` 中。默认情况下，Evennia 的 `STATIC_ROOT` 位于 `web/static`。

由于 Django 从所有这些单独的位置提取文件并将它们放入一个文件夹中，因此可能会出现一个文件覆盖另一个文件的情况。我们将利用这一点插入自己的文件，而无需更改 Evennia 本身的任何内容。

默认情况下，Evennia 被配置为在加载所有其他静态文件 *之后* 提取您放置在 `mygame/web/static/` 中的文件。这意味着在 `mygame/web/static/` 文件夹下的文件将覆盖之前加载的 *具有相同路径下的文件*。这一点非常重要，需要重复强调：要覆盖来自标准 `evennia/web/static` 文件夹的静态资源，您需要在 `mygame/web/static/` 下复制文件名和文件夹的路径。幸运的是，您的游戏目录已具备许多预先制作的结构，因此应该很明确：例如，要覆盖网站相关的内容，您将其放在 `mygame/web/static/website/` 下。Web 客户端会放在 `mygame/web/static/webclient` 下，依此类推。

让我们看看这如何适用于我们的 logo。默认的 Web 应用程序位于 Evennia 库本身中，即 `evennia/web/`。我们可以看到这里有一个 `static` 文件夹。如果我们继续浏览，最终会找到 Evennia logo 文件的完整路径：`evennia/web/static/website/images/evennia_logo.png`。

将您自己的 logo 放在您的游戏文件夹中的相应位置：`mygame/web/static/website/images/evennia_logo.png`。

为了使这个文件生效，只需切换到您的游戏目录并重新加载服务器：

```
evennia reload
```

这将重新加载配置并引入新静态文件。如果您不想重新加载服务器，也可以使用

```
evennia collectstatic
```

仅更新静态文件，而无需进行其他更改。

> Evennia 会在启动时自动收集静态文件。因此，如果 `evennia collectstatic` 报告找到 0 个要收集的文件，请确保您没有在某个时候启动引擎 - 如果是，这样收集器就已经做过工作！为确保这一点，请连接到网站并检查 logo 是否已实际更改为您自己的版本。

> 资产收集器实际上将所有数据收集到一个地方，即隐藏的目录 `mygame/server/.static/`。这些文件就是从这里提供的。有时静态资产收集器可能会混淆。如果不管您怎么做，您的覆盖文件都没有复制到默认文件上，请尝试清空 `mygame/server/.static/` 文件夹，然后重新运行 `evennia collectstatic`。

## 更改首页文本

Evennia 的默认首页包含有关 Evennia 项目的信息。您可能希望用您自己项目的信息替换这些信息。更改页面模板的方式与更改静态资源的方式相似。

与静态文件一样，Django 会在一系列模板文件夹中查找所需的文件。不同之处在于，Django 不会将所有模板文件复制到一个地方，而是仅搜索模板文件夹，直到找到匹配的模板。这意味着当您编辑模板时，所做的更改是即时的。您不必重新加载服务器或运行任何额外命令来查看这些更改 - 在浏览器中重新加载网页就足够了。

要替换索引页的文本，我们需要找到其模板。有关如何确定渲染页面所使用的模板的更多细节，请参考 [基于 Web 的角色视图教程](./Web-Character-View-Tutorial.md)。现在，您应该知道我们想要更改的模板存储在 `evennia/web/website/templates/website/index.html` 中。

要替换此模板文件，您需要将更改后的模板放在 `mygame/web/templates/` 中。与静态资源一样，您必须复制与主库中相同的文件夹结构。例如，要覆盖在 `evennia/web/templates/website/index.html` 中找到的主 `index.html` 文件，请将其复制到 `mygame/web/templates/website/index.html` 并根据需要自定义它。只需重新加载服务器以查看您的新版本。

## 进一步阅读

有关处理 Web 存在的更多提示，您可以继续阅读 [基于 Web 的角色视图教程](./Web-Character-View-Tutorial.md)，在其中您可以学习制作显示游戏角色统计信息的网页。您还可以查看 [Django 的教程](https://docs.djangoproject.com/en/4.1/intro/tutorial01/) 以更深入地了解 Django 的工作原理和存在的可能性。
