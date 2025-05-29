# 国际化

*国际化*（通常缩写为 *i18n*，因为在这个词中，首字母 "i" 和末尾字母 "n" 之间有 18 个字符）允许 Evennia 的核心服务器返回其他语言的文本，而无需编辑源代码。

语言翻译由志愿者完成，因此支持程度可能会有所不同，具体取决于某种语言最近一次更新的时间。以下是所有具有一定支持水平的语言（除了英语）。通常，任何在 2022 年 9 月之后未更新的语言都会缺少一些翻译。

```plaintext
+---------------+----------------------+--------------+
| Language Code | Language             | Last updated |
+===============+======================+==============+
| de            | German               | Aug 2024     |
+---------------+----------------------+--------------+
| es            | Spanish              | Aug 2019     |
+---------------+----------------------+--------------+
| fr            | French               | Dec 2022     |
+---------------+----------------------+--------------+
| it            | Italian              | Oct 2022     |
+---------------+----------------------+--------------+
| ko            | Korean (simplified)  | Sep 2019     |
+---------------+----------------------+--------------+
| la            | Latin                | Feb 2021     |
+---------------+----------------------+--------------+
| pl            | Polish               | Apr 2024     |
+---------------+----------------------+--------------+
| pt            | Portuguese           | Oct 2022     |
+---------------+----------------------+--------------+
| ru            | Russian              | Apr 2020     |
+---------------+----------------------+--------------+
| sv            | Swedish              | Sep 2022     |
+---------------+----------------------+--------------+
| zh            | Chinese (simplified) | Oct 2024     |
+---------------+----------------------+--------------+
```

语言翻译文件位于 [evennia/locale](github:evennia/locale/) 文件夹中。如果你想帮助改进现有翻译或贡献新的翻译，请阅读下文。

## 更改服务器语言

通过在 `mygame/server/conf/settings.py` 文件中添加以下内容来更改语言：

```python
USE_I18N = True
LANGUAGE_CODE = 'en'
```

这里的 `'en'`（默认英语）应更改为 `locale/` 中支持语言的缩写（以及上面的列表中）。重启服务器以激活 i18n。

```{important}
即使是“完全翻译”的语言，在启动 Evennia 时你仍会看到许多地方是英文的。这是因为我们期望你（开发者）懂英语（毕竟你正在阅读本手册）。因此，我们翻译了*最终玩家可能看到的硬编码字符串*——这些是你无法轻易从 mygame/ 文件夹中更改的内容。命令和类型类的输出通常*不*翻译，控制台/日志输出也不翻译。

为了减少工作量，你可以考虑只翻译面向玩家的命令（如 look、get 等），并将默认的管理命令保留为英语。要更改某些命令（如 `look`）的语言，你需要覆盖类型类上的相关钩子方法（查看默认命令的代码以了解其调用内容）。
```

```{sidebar} Windows 用户
如果在 Windows 上遇到有关 `gettext` 或 `xgettext` 的错误，请参阅 [Django 文档](https://docs.djangoproject.com/en/4.1/topics/i18n/translation/#gettext-on-windows)。一个自安装且最新的 Windows 版 gettext（32/64 位）可在 Github 上的 [gettext-iconv-windows](https://github.com/mlocati/gettext-iconv-windows) 找到。
```

## 翻译 Evennia

翻译文件位于核心 `evennia/` 库中的 `evennia/evennia/locale/` 下。在继续之前，你必须确保已从 [Evennia 的 github](github:evennia) 克隆了此存储库。

如果在 `evennia/evennia/locale/` 中找不到你的语言，那是因为还没有人翻译它。或者你可能有该语言，但觉得翻译不好……欢迎你帮助改善这种情况！

要开始新的翻译，你需要先用 GIT 克隆 Evennia 存储库，并按照 [安装快速入门](../Setup/Installation.md) 页面所述激活一个 Python 虚拟环境。

进入 `evennia/evennia/` 目录——即，不是你的游戏目录，而是 `evennia/` 存储库本身。如果你看到 `locale/` 文件夹，说明你在正确的位置。确保你的 `virtualenv` 是激活的，以便 `evennia` 命令可用。然后运行

```bash
evennia makemessages --locale <language-code>
```

其中 `<language-code>` 是你要翻译的语言的[两字母语言代码](http://www.science.co.il/Language/Codes.asp)，例如瑞典语的 'sv' 或西班牙语的 'es'。片刻之后，它会告诉你该语言已被处理。例如：

```bash
evennia makemessages --locale sv
```

如果你开始了一种新语言，`locale/` 文件夹中会出现一个该语言的新文件夹。否则，系统只会更新现有翻译，并在服务器中找到新的字符串。运行此命令不会覆盖任何现有字符串，因此你可以随意多次运行。

接下来，前往 `locale/<language-code>/LC_MESSAGES` 并编辑你在那里找到的 `**.po` 文件。你可以用普通文本编辑器编辑它，但使用网络上的特殊 po 文件编辑器最简单（在网上搜索“po 编辑器”可以找到许多免费选择），例如：

- [gtranslator](https://wiki.gnome.org/Apps/Gtranslator)
- [poeditor](https://poeditor.com/)

翻译的概念很简单，就是尽你所能将 `django.po` 文件中的英文字符串翻译成你的语言。一旦完成，运行

```bash
evennia compilemessages
```

这将编译所有语言。检查你的语言，并返回到你的 `.po` 文件中查看该过程是否更新了它——你可能需要填写一些缺失的头字段，并通常应该注明谁进行了翻译。

完成后，确保每个人都能从你的翻译中受益！用更新的 `django.po` 文件对 Evennia 提交一个 PR。如果你不擅长使用 git，可以将其附加到我们论坛的新帖子中。

### 翻译提示

许多翻译字符串使用 `{ ... }` 占位符。这是因为它们将在 `.format()` Python 操作中使用。虽然如果在你的语言中更有意义，你可以更改这些的*顺序*，但你*不能*翻译这些格式化标签中的变量——Python 会查找它们！

```plaintext
Original: "|G{key} connected|n"
Swedish:  "|G{key} anslöt|n"
```

你还必须保留消息开头和结尾的换行符（如果有的话，你的 po 编辑器应该会阻止你不这样做）。尽量也以相同的句子分隔符结束（如果在你的语言中有意义的话）。

```plaintext
Original: "\n(Unsuccessfull tried '{path}')."
Swedish: "\nMisslyckades med att nå '{path}')."
```

最后，试着了解字符串是为谁准备的。如果使用了特殊的技术术语，那么翻译它可能比不翻译更令人困惑，即使它在 `{...}` 标签之外。混合使用英语和你的语言可能比你强行翻译某个术语更清晰，因为每个人通常都会以英语阅读它。

```plaintext
Original: "\nError loading cmdset: No cmdset class '{classname}' in '{path}'.
           \n(Traceback was logged {timestamp})"
Swedish:  "Fel medan cmdset laddades: Ingen cmdset-klass med namn '{classname}' i {path}.
           \n(Traceback loggades {timestamp})"
```

## 在代码中标记字符串以供翻译

如果你修改了 Python 模块代码，可以通过将字符串传递给 `gettext()` 方法来标记它们以供翻译。在 Evennia 中，通常将其导入为 `_()` 以方便使用：

```python
from django.utils.translation import gettext as _
string = _("Text to translate")
```

### 格式化注意事项

使用格式化字符串时，确保首先将“原始”字符串传递给 `gettext` 进行翻译，然后再格式化输出。否则，占位符将在翻译发生之前被替换，导致无法在 `.po` 文件中找到正确的字符串。还建议使用命名占位符（例如 `{char}`）而不是位置占位符（例如 `{}`），以提高可读性和可维护性。

```python
# 错误示例：
string2 = _("Hello {char}!".format(char=caller.name))

# 正确示例：
string2 = _("Hello {char}!").format(char=caller.name)
```

这也是为什么 f-strings 无法与 `gettext` 一起使用的原因：

```python
# 不会工作
string = _(f"Hello {char}!")
```
