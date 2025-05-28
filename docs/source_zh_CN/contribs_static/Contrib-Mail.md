# 游戏内邮件系统

由 grungies1138 贡献，2016

这是一个简单的 Brandymail 风格邮件系统，使用 Evennia Core 的 `Msg` 类。它提供了两个命令，用于在账户之间（游戏外）或角色之间（游戏内）发送邮件。这两种类型的邮件可以一起使用，也可以单独使用。

- `CmdMail` - 应该放在账户命令集上，使 `mail` 命令在 IC 和 OOC 模式下都可用。邮件将始终发送到账户（其他玩家）。
- `CmdMailCharacter` - 应该放在角色命令集上，使 `mail` 命令仅在控制角色时可用。邮件将仅发送给其他角色，并且在 OOC 模式下不可用。
- 如果将*两个*命令添加到各自的命令集中，您将获得两个独立的 IC 和 OOC 邮件系统，IC 和 OOC 模式下的邮件列表不同。

## 安装：

安装以下一个或两个（见上文）：

- CmdMail（IC + OOC 邮件，玩家之间发送）

    ```python
    # mygame/commands/default_cmds.py

    from evennia.contrib.game_systems import mail

    # 在 AccountCmdSet.at_cmdset_creation 中：
        self.add(mail.CmdMail())
    ```
- CmdMailCharacter（可选，仅 IC 邮件，角色之间发送）

    ```python
    # mygame/commands/default_cmds.py

    from evennia.contrib.game_systems import mail

    # 在 CharacterCmdSet.at_cmdset_creation 中：
        self.add(mail.CmdMailCharacter())
    ```
安装后，在游戏中使用 `help mail` 获取有关邮件命令的帮助。使用 `ic/ooc` 切换进入和退出 IC/OOC 模式。
