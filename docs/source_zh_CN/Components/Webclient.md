# Web 客户端

Evennia 提供了一个可以通过普通网页浏览器访问的 MUD 客户端。在开发过程中，你可以在 `http://localhost:4001/webclient` 进行尝试。客户端由几个部分组成，全部位于 `evennia/web` 目录下：

- `templates/webclient/webclient.html` 和 `templates/webclient/base.html` 是非常简单的 Django HTML 模板，用于描述 webclient 的布局。

- `static/webclient/js/evennia.js` 是主要的 Evennia JavaScript 库。它处理 Evennia 与客户端之间通过 WebSockets 的所有通信，如果浏览器不支持 WebSockets，则通过 AJAX/COMET。它会将 Evennia 对象提供给 JavaScript 命名空间，提供用于透明地向服务器发送和接收数据的方法。这也可以用于替换 GUI 前端。

- `static/webclient/js/webclient_gui.js` 是默认的插件管理器。它将 `plugins` 和 `plugin_manager` 对象添加到 JavaScript 命名空间，协调各种插件之间的 GUI 操作，并使用 Evennia 对象库进行所有输入/输出。

- `static/webclient/js/plugins` 提供了一组默认插件，实现了一个“类似 Telnet”的接口，以及几个示例插件，展示如何实现新的插件功能。

- `static/webclient/css/webclient.css` 是客户端的 CSS 文件；它还定义了如何显示 ANSI/Xterm256 颜色等。

服务器端的 webclient 协议位于 `evennia/server/portal/webclient.py` 和 `webclient_ajax.py` 中，分别用于两种类型的连接。你不能（也不需要）修改这些。

## 自定义 Web 客户端

与网站的情况类似，你可以从你的游戏目录中覆盖 webclient。你需要在项目的 `mygame/web/` 目录中添加/修改一个文件。这些目录在游戏运行时不会被 Web 服务器直接使用，服务器会将 Evennia 文件夹中所有与 Web 相关的内容复制到 `mygame/server/.static/`，然后再复制所有 `mygame/web/` 文件。这可能会导致你编辑了一个文件，但服务器的行为没有变化的情况。**在做任何其他事情之前，尝试关闭游戏并从命令行运行 `evennia collectstatic`，然后重新启动游戏，清除浏览器缓存，看看你的编辑是否显示出来。**

例如：要更改正在使用的插件列表，你需要通过复制 `evennia/web/templates/webclient/base.html` 到 `mygame/web/templates/webclient/base.html` 并编辑它来覆盖 base.html，以添加你的新插件。

## Evennia Web 客户端 API（来自 evennia.js）
- `Evennia.init( opts )`
- `Evennia.connect()`
- `Evennia.isConnected()`
- `Evennia.msg( cmdname, args, kwargs, callback )`
- `Evennia.emit( cmdname, args, kwargs )`
- `log()`

## 插件管理器 API（来自 webclient_gui.js）
- `options` 对象，存储键/值“状态”，可由插件用于协调行为。
- `plugins` 对象，所有加载的插件的键/值列表。
- `plugin_handler` 对象
  - `plugin_handler.add("name", plugin)`
  - `plugin_handler.onSend(string)`

## 插件回调 API
- `init()` -- 唯一必需的回调
- `boolean onKeydown(event)` 该插件监听 Keydown 事件
- `onBeforeUnload()` 该插件在 webclient 页面/标签关闭之前执行某些特殊操作。
- `onLoggedIn(args, kwargs)` 该插件在 webclient 首次登录时执行某些操作。
- `onGotOptions(args, kwargs)` 该插件处理从服务器发送的选项。
- `boolean onText(args, kwargs)` 该插件处理从服务器发送的消息。
- `boolean onPrompt(args, kwargs)` 该插件在服务器发送提示时执行某些操作。
- `boolean onUnknownCmd(cmdname, args, kwargs)` 该插件处理“未知命令”。
- `onConnectionClose(args, kwargs)` 该插件在 webclient 从服务器断开连接时执行某些操作。
- `newstring onSend(string)` 该插件检查/修改其他插件生成的文本。**谨慎使用**

在 `base.html` 中定义的插件顺序很重要。每个插件的所有回调将按该顺序执行。上面标记为“boolean”的函数必须返回 true/false。返回 true 将短路执行，因此 `base.html` 列表中较低的其他插件将不会调用其该事件的回调。这使得像 history.js 插件的上下箭头键总是在 default_in.js 插件将该键添加到当前输入缓冲区之前发生。

### 示例/默认插件 (`plugins/*.js`)

- `clienthelp.js` 定义了来自 options2 插件的 onOptionsUI。 这是一个主要为空的插件，用于为你的游戏添加一些“如何”信息。
- `default_in.js` 定义了 onKeydown。 `<enter>` 键或鼠标点击箭头将发送当前输入的文本。
- `default_out.js` 定义了 onText、onPrompt 和 onUnknownCmd。 为用户生成 HTML 输出。
- `default_unload.js` 定义了 onBeforeUnload。 提示用户确认他们是否打算离开/关闭游戏。
- `font.js` 定义了 onOptionsUI。 该插件添加了选择字体和字体大小的功能。
- `goldenlayout_default_config.js` 实际上不是一个插件，定义了一个全局变量，goldenlayout 用于确定其窗口布局、已知标签路由等。
- `goldenlayout.js` 定义了 onKeydown、onText 和自定义函数。 一个非常强大的“标签式”窗口管理器，用于拖放窗口、文本路由等。
- `history.js` 定义了 onKeydown 和 onSend。 创建一个已发送命令的历史记录，并使用箭头键浏览。
- `hotbuttons.js` 定义了 onGotOptions。 一个默认禁用的插件，定义了一个带有用户可分配命令的按钮栏。
- `html.js` 一个基本插件，允许客户端处理来自服务器的“原始 html”消息，这允许服务器发送本机 HTML 消息，如 `<div style='s'>styled text</div>`
- `iframe.js` 定义了 onOptionsUI。 一个仅限 goldenlayout 的插件，用于创建一个受限浏览子窗口，用于并排的 web/text 界面，主要是一个如何为 goldenlayout 构建新 HTML“组件”的示例。
- `message_routing.js` 定义了 onOptionsUI、onText、onKeydown。 这个仅限 goldenlayout 的插件实现了正则表达式匹配，允许用户“标记”匹配的任意文本，以便将其路由到正确的窗口。 类似于其他客户端的“生成”功能。
- `multimedia.js` 一个基本插件，允许客户端处理来自服务器的“图像”、“音频”和“视频”消息，并将其显示为内联 HTML。
- `notifications.js` 定义了 onText。 为每条新消息生成浏览器通知事件，而标签页处于隐藏状态。
- `oob.js` 定义了 onSend。 允许用户测试/发送带外 json 消息到服务器。
- `options.js` 定义了大多数回调。 提供一个基于弹出窗口的 UI，以协调与服务器的选项设置。
- `options2.js` 定义了大多数回调。 提供一个基于 goldenlayout 的选项/设置选项卡版本。 通过自定义 onOptionsUI 回调与其他插件集成。
- `popups.js` 为其他插件提供默认的弹出/对话 UI。
- `text2html.js` 提供了一种新的消息处理器类型：`text2html`，类似于多媒体和 html 插件。 该插件提供了一种将常规管道样式的 ASCII 消息卸载到客户端进行渲染的方法。 这允许服务器减少工作，同时也允许客户端自定义此转换过程。 要使用此插件，你需要覆盖 Evennia 中的当前命令，更改任何生成原始文本输出消息的地方，并将其转换为 `text2html` 消息。 例如：`target.msg("my text")` 变为：`target.msg(text2html=("my text"))`（更好的是，使用 webclient 窗格路由标签：`target.msg(text2html=("my text", {"type": "sometag"}))`）`text2html` 消息应格式化并表现得与服务器端生成的 text2html() 输出相同。

### 关于 html 消息与 text2html 消息的附注

假设你希望让你的 webclient 输出更像标准网页...
对于 telnet 客户端，你可以收集一堆文本行，带有 ASCII 格式的边框等。然后将结果发送到客户端通过 text2html 插件进行渲染。

但对于 webclient，你可以直接使用 html 插件格式化消息，将整个内容渲染为 HTML 表格，如下所示：

```python
# 服务器端 Python 代码：

if target.is_webclient():
    # 这可以使用 CSS 进行样式化，只需将 CSS 文件添加到 web/static/webclient/css/...
    table = [
             "<table>",
              "<tr><td>1</td><td>2</td><td>3</td></tr>",
              "<tr><td>4</td><td>5</td><td>6</td></tr>",
             "</table>"
           ]
    target.msg( html=( "".join(table), {"type": "mytag"}) )
else:
    # 这将使用客户端将其渲染为“简单的” ASCII 文本，与通过门户的 text2html() 函数在服务器端渲染的效果相同
    table = [ 
            "#############",
            "# 1 # 2 # 3 #",
            "#############",
            "# 4 # 5 # 6 #",
            "#############"
           ]
    target.msg( html2html=( "\n".join(table), {"type": "mytag"}) )
```

## 编写你自己的插件

所以，你喜欢 webclient 的功能，但你的游戏有特定类型的文本需要在视觉上分离到它们自己的空间中。Goldenlayout 插件框架可以帮助实现这一点。

### GoldenLayout

GoldenLayout 是一个 web 框架，允许 web 开发人员及其用户创建自己的标签/窗口布局。窗口/标签可以通过点击其标题栏并拖动到“框架线”出现的位置，从一个位置拖动到另一个位置。将窗口拖动到另一个窗口的标题栏上将创建一个标签式“堆栈”。Evennia 的 goldenlayout 插件定义了 3 种基本类型的窗口：主窗口、输入窗口和非主文本输出窗口。主窗口和第一个输入窗口是唯一不能“关闭”的窗口。

最基本的自定义是为你的用户提供一个默认布局，而不仅仅是一个主输出和一个起始输入窗口。这是通过修改服务器的 goldenlayout_default_config.js 来完成的。

首先，创建一个新的 `mygame/web/static/webclient/js/plugins/goldenlayout_default_config.js` 文件，并添加以下 JSON 变量：

```javascript
var goldenlayout_config = {
    content: [{
        type: 'column',
        content: [{
            type: 'row',
            content: [{
                type: 'column',
                content: [{
                    type: 'component',
                    componentName: 'Main',
                    isClosable: false,
                    tooltip: 'Main - drag to desired position.',
                    componentState: {
                        cssClass: 'content',
                        types: 'untagged',
                        updateMethod: 'newlines',
                    },
                }, {
                    type: 'component',
                    componentName: 'input',
                    id: 'inputComponent',
                    height: 10,
                    tooltip: 'Input - The last input in the layout is always the default.',
                }, {
                    type: 'component',
                    componentName: 'input',
                    id: 'inputComponent',
                    height: 10,
                    isClosable: false,
                    tooltip: 'Input - The last input in the layout is always the default.',
                }]
            },{
                type: 'column',
                content: [{
                    type: 'component',
                    componentName: 'evennia',
                    componentId: 'evennia',
                    title: 'example',
                    height: 60,
                    isClosable: false,
                    componentState: {
                        types: 'some-tag-here',
                        updateMethod: 'newlines',
                    },
                }, {
                    type: 'component',
                    componentName: 'evennia',
                    componentId: 'evennia',
                    title: 'sheet',
                    isClosable: false,
                    componentState: {
                        types: 'sheet',
                        updateMethod: 'replace',
                    },
                }],
            }],
        }]
    }]
};
```

这有点复杂，但希望从缩进中你可以看到它创建了一个并排的（2 列）界面，左侧有 3 个窗口（主窗口和 2 个输入窗口），右侧有一对窗口用于额外的输出。任何标记为 "some-tag-here" 的文本将流向 "example" 窗口的底部，任何标记为 "sheet" 的文本将替换 "sheet" 窗口中已有的文本。

注意：GoldenLayout 如果创建两个具有 "Main" componentName 的窗口会非常困惑并且会崩溃。

现在，假设你想在每个窗口上使用不同的 CSS 显示文本。这就是新的 goldenlayout "组件" 的用武之地。每个组件就像一个蓝图，当你创建该组件的新实例时会被盖章，一旦定义，就不会轻易更改。你需要定义一个新组件，最好是在一个新的插件文件中，然后将其添加到你的页面中（可以通过 JavaScript 动态地添加到 DOM，或者通过将新插件文件包含到 base.html 中）。

首先，按照上面自定义 Web 客户端部分中的说明覆盖 base.html。

接下来，将新插件添加到你的 base.html 副本中：

```html
<script src={% static "webclient/js/plugins/myplugin.js" %} language="javascript"
type="text/javascript"></script>
```
记住，插件是加载顺序相关的，所以请确保新的 `<script>` 标签位于 `goldenlayout.js` 之前。

接下来，创建一个新的插件文件 `mygame/web/static/webclient/js/plugins/myplugin.js` 并编辑它。

```javascript
let myplugin = (function () {
    //
    //
    var postInit = function() {
        var myLayout = window.plugins['goldenlayout'].getGL();

        // 注册我们的组件并替换默认的消息窗口
        myLayout.registerComponent( 'mycomponent', function (container, componentState) {
            let mycssdiv = $('<div>').addClass('myCSS');
            mycssdiv.attr('types', 'mytag');
            mycssdiv.attr('update_method', 'newlines');
            mycssdiv.appendTo( container.getElement() );
        });

        console.log("MyPlugin Initialized.");
    }

    return {
        init: function () {},
        postInit: postInit,
    }
})();
window.plugin_handler.add("myplugin", myplugin);
```
然后你可以将 "mycomponent" 添加到 `goldenlayout_default_config.js` 中项目的 `componentName` 中。

确保停止你的服务器，执行 `evennia collectstatic`，并重新启动你的服务器。然后确保在加载 webclient 页面之前清除浏览器缓存。
