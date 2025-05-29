# Bootstrap 前端框架

Evennia 的默认网页使用了一个名为 [Bootstrap](https://getbootstrap.com/) 的框架。这个框架在互联网上被广泛使用——一旦你学会了一些常见的设计模式，你可能会开始识别出它的影响。对于像你这样的网页开发者来说，这种切换是很棒的，因为我们有一个基础，一个起点来工作，而不是纠结于设置不同的网格系统或其他设计师使用了什么自定义类。Bootstrap 默认是响应式的，并且带有一些默认样式，Evennia 对这些样式进行了轻微的覆盖，以保留你从之前设计中习惯的某些颜色和样式。

以下是 Bootstrap 的简要概述。欲了解更深入的信息，请阅读 [官方文档](https://getbootstrap.com/docs/4.0/getting-started/introduction/)。

## 网格系统

除了基本的样式，Bootstrap 还包括 [内置的布局和网格系统](https://getbootstrap.com/docs/4.0/layout/overview/)。

### 容器

网格系统的第一部分是 [容器](https://getbootstrap.com/docs/4.0/layout/overview/#containers)。

容器用于容纳你所有的页面内容。Bootstrap 提供两种类型：固定宽度和全宽度。固定宽度容器占据页面的某个最大宽度——它们对于限制桌面或平板平台上的宽度很有用，而不是让内容跨越整个页面宽度。

```html
<div class="container">
    <!--- 你的内容在这里 -->
</div>
```

全宽度容器占据可用的最大宽度——它们会跨越宽屏桌面或较小屏幕手机，从边到边。

```html
<div class="container-fluid">
    <!--- 这个内容将跨越整个页面 -->
</div>
```

### 网格

布局系统的第二部分是 [网格](https://getbootstrap.com/docs/4.0/layout/grid/)。

这是 Bootstrap 布局的核心——它允许你根据屏幕大小更改元素的大小，而无需编写任何媒体查询。我们将简要介绍一下——要了解更多，请阅读文档或在浏览器中查看 Evennia 首页的源代码。

> 重要提示！网格元素应该位于 .container 或 .container-fluid 中。这将使你网站的内容居中。

Bootstrap 的网格系统允许你通过应用基于断点的类来创建行和列。默认的断点是超小、小、中、大和超大。如果你想了解更多关于这些断点的信息，请 [查看文档](https://getbootstrap.com/docs/4.0/layout/overview/#responsive-breakpoints)。

要使用网格系统，首先为你的内容创建一个容器，然后像这样添加行和列：

```html
<div class="container">
    <div class="row">
        <div class="col">
           1 of 3
        </div>
        <div class="col">
           2 of 3
        </div>
        <div class="col">
           3 of 3
        </div>
    </div>
</div>
```

这个布局将创建三个等宽的列。

要指定你的尺寸——例如，Evennia 的默认网站在桌面和平板上有三列，但在较小的屏幕上重新排列为单列。试试看！

```html
<div class="container">
    <div class="row">
        <div class="col col-md-6 col-lg-3">
            1 of 4
        </div>
        <div class="col col-md-6 col-lg-3">
            2 of 4
        </div>
        <div class="col col-md-6 col-lg-3">
            3 of 4
        </div>
        <div class="col col-md-6 col-lg-3">
            4 of 4
        </div>
    </div>
</div>
```

这个布局将在大屏幕上是 4 列，在中等屏幕上是 2 列，而在任何更小的屏幕上是 1 列。

要了解更多关于 Bootstrap 网格的信息，请 [查看文档](https://getbootstrap.com/docs/4.0/layout/grid/)。

## 通用样式元素

Bootstrap 为你的网站提供基础样式。这些样式可以通过 CSS 自定义，但默认样式旨在为网站提供一致、干净的外观。

### 颜色

大多数元素可以使用默认颜色进行样式化。[查看文档](https://getbootstrap.com/docs/4.0/utilities/colors/)以了解更多关于这些颜色的信息——简单来说，添加一个 text-* 或 bg-* 类，例如 text-primary，可以设置文本颜色或背景颜色。

### 边框

只需为元素添加一个 'border' 类即可为元素添加边框。欲了解更深入的信息，请 [阅读边框文档](https://getbootstrap.com/docs/4.0/utilities/borders/)。

```html
<span class="border border-dark"></span>
```

你也可以通过添加一个类轻松地圆角。

```html
<img src="..." class="rounded" />
```

### 间距

Bootstrap 提供类以轻松添加响应式的边距和填充。大多数情况下，你可能希望通过 CSS 本身添加边距或填充——然而这些类在默认的 Evennia 网站中使用。[查看文档](https://getbootstrap.com/docs/4.0/utilities/spacing/)以了解更多。

### 按钮

在 Bootstrap 中，[按钮](https://getbootstrap.com/docs/4.0/components/buttons/) 非常易于使用——按钮样式可以添加到 `<button>`、`<a>` 和 `<input>` 元素中。

```html
<a class="btn btn-primary" href="#" role="button">I'm a Button</a>
<button class="btn btn-primary" type="submit">Me too!</button>
<input class="btn btn-primary" type="button" value="Button">
<input class="btn btn-primary" type="submit" value="Also a Button">
<input class="btn btn-primary" type="reset" value="Button as Well">
```

### 卡片

[卡片](https://getbootstrap.com/docs/4.0/components/card/) 为其他元素提供了一个容器，使其从页面的其他部分脱颖而出。默认网页上的 "Accounts"、"Recently Connected" 和 "Database Stats" 都在卡片中。卡片提供了相当多的格式选项——以下是一个简单的示例，但请阅读文档或查看网站的源代码以了解更多。

```html
<div class="card">
  <div class="card-body">
    <h4 class="card-title">Card title</h4>
    <h6 class="card-subtitle mb-2 text-muted">Card subtitle</h6>
    <p class="card-text">Fancy, isn't it?</p>
    <a href="#" class="card-link">Card link</a>
  </div>
</div>
```

### Jumbotron

[Jumbotrons](https://getbootstrap.com/docs/4.0/components/jumbotron/) 对于展示游戏的图像或标语非常有用。它们可以与其他内容一起流动，也可以占据页面的全宽度——Evennia 的基础网站使用前者。

```html
<div class="jumbotron jumbotron-fluid">
  <div class="container">
    <h1 class="display-3">Full Width Jumbotron</h1>
    <p class="lead">Look at the source of the default Evennia page for a regular Jumbotron</p>
  </div>
</div>
```

### 表单

[表单](https://getbootstrap.com/docs/4.0/components/forms/) 在 Bootstrap 中高度可定制。要更深入地了解如何在你自己的 Evennia 网站中使用表单及其样式，请阅读 [网页角色生成教程](../Howtos/Web-Character-Generation.md)。

## 进一步阅读

Bootstrap 还提供了大量的实用工具，以及样式和内容元素。要了解更多关于它们的信息，请 [阅读 Bootstrap 文档](https://getbootstrap.com/docs/4.0/getting-started/introduction/) 或阅读我们其他的网页教程。
