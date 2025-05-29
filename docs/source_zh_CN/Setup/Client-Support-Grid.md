# 客户端支持网格

此网格试图收集不同 MU 客户端与 Evennia 配合使用时的信息。如果你想报告问题、更新条目或添加客户端，请为其创建一个新的[文档问题](github:issue)。鼓励大家报告他们的发现。

## 客户端网格

图例：

- **名称**：客户端的名称。还请注意它是否特定于某个操作系统。
- **版本**：测试过的客户端版本或版本范围。
- **备注**：使用此客户端与 Evennia 配合时的任何特殊情况都应在此添加。

| 名称 | 版本测试 | 备注 |
| --- | --- | --- |
| [Evennia Webclient][1]    | 1.0+      | 特定于 Evennia |
| [tintin++][2]             | 2.0+      | 不支持 MXP  |
| [tinyfugue][3]            | 5.0+      | 不支持 UTF-8                                               |
| [MUSHclient][4] (Win)     | 4.94      | NAWS 报告完整文本区域                                    |
| [Zmud][5] (Win)           | 7.21      | *未测试*                                                     |
| [Cmud][6] (Win)           | v3        | *未测试*                                                     |
| [Potato][7]              | 2.0.0b16  | 不支持 MXP、MCCP。Win 32 位不理解            |
|                           |           | "localhost"，必须使用 `127.0.0.1`。                             |
| [Mudlet][8]               | 3.4+      | 无已知问题。某些旧版本在 MXP 下显示 <> 为 html         |
|                           |           | 。                                                     |
| [SimpleMU][9] (Win)       | 完整      | 已停产。NAWS 报告像素大小。                         |
| [Atlantis][10] (Mac)      | 0.9.9.4   | 无已知问题。                                               |
| [GMUD][11]                | 0.0.1     | 无法处理任何 telnet 握手。不推荐。          |
| [BeipMU][12] (Win)        | 3.0.255   | 不支持 MXP。最好启用“MUD 提示处理”，禁用  |
|                           |           | “处理 HTML 标签”。                                            |
| [MudRammer][13] (IOS)     | 1.8.7     | 不良的 Telnet 协议兼容性：显示虚假字符。  |
| [MUDMaster][14]           | 1.3.1     | *未测试*                                                     |
| [BlowTorch][15] (Andr)    | 1.1.3     | Telnet NOP 显示为虚假字符。                     |
| [Mukluk][16] (Andr)       | 2015.11.20| Telnet NOP 显示为虚假字符。支持 UTF-8/Emoji     |
|                           |           | 。                                                       |
| [Gnome-MUD][17] (Unix)    | 0.11.2    | Telnet 握手错误。第一次（唯一一次）尝试登录    |
|                           |           | 失败。                                                         |
| [Spyrit][18]              | 0.4       | 不支持 MXP、OOB。                                           |
| [JamochaMUD][19]          | 5.2       | 不支持 MXP 文本中的 ANSI。                         |
| [DuckClient][20] (Chrome) | 4.2       | 不支持 MXP。显示 Telnet Go-Ahead 和                   |
|                           |           | WILL SUPPRESS-GO-AHEAD 为 ù 字符。似乎还会在连接时运行       |
|                           |           | `version` 命令，这在 `MULTISESSION_MODES` 大于 1 时不起作用。                                  |
| [KildClient][21]          | 2.11.1    | 无已知问题。                                               |

[1]: ../Components/Webclient
[2]: http://tintin.sourceforge.net/
[3]: http://tinyfugue.sourceforge.net/
[4]: https://mushclient.com/
[5]: http://forums.zuggsoft.com/index.php?page=4&action=file&file_id=65
[6]: http://forums.zuggsoft.com/index.php?page=4&action=category&cat_id=11
[7]: https://www.potatomushclient.com/
[8]: https://www.mudlet.org/
[9]: https://archive.org/details/tucows_196173_SimpleMU_MU_Client
[10]: https://www.riverdark.net/atlantis/
[11]: https://sourceforge.net/projects/g-mud/
[12]: http://www.beipmu.com/
[13]: https://itunes.apple.com/us/app/mudrammer-a-modern-mud-client/id597157072
[14]: https://itunes.apple.com/us/app/mudmaster/id341160033
[15]: https://bt.happygoatstudios.com/
[16]: https://play.google.com/store/apps/details?id=com.crap.mukluk
[17]: https://github.com/GNOME/gnome-mud
[18]: https://spyrit.ierne.eu.org/
[19]: https://jamochamud.org/
[20]: http://duckclient.com/
[21]: https://www.kildclient.org/

## 客户端问题的解决方法：

### 问题：Telnet NOP 显示为虚假字符。

已知客户端：

- BlowTorch (Andr)
- Mukluk (Andr)

解决方法：

- 游戏内：使用 `@option NOPKEEPALIVE=off` 关闭会话，或使用 `/save` 参数永久禁用该 Evennia 帐户。
- 客户端：设置一个对 NOP 字符的屏蔽触发器，使其在客户端中不可见。
