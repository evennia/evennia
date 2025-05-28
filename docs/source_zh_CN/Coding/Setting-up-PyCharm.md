# 在 PyCharm 中设置 Evennia

[PyCharm](https://www.jetbrains.com/pycharm/) 是 Jetbrains 提供的一个适用于 Windows、Mac 和 Linux 的 Python 开发者 IDE。它是一个商业产品，但提供免费试用、精简的社区版，以及对像 Evennia 这样的开源项目的慷慨许可。

首先，下载并安装您选择的 IDE 版本。社区版应该包含您所需的一切，但专业版具有集成的 Django 支持，这可能会有所帮助。

## 从现有项目开始

如果您想在已经存在的 Evennia 游戏中使用 PyCharm，请使用此方法。首先，确保您已完成[此处](https://www.evennia.com/docs/latest/Setup/Installation.html#requirements)列出的步骤，尤其是 virtualenv 部分，这将使 IDE 设置更简单。

1. 打开 PyCharm 并点击打开按钮，打开与 `mygame/` 对应的根文件夹。
2. 点击 文件 -> 设置 -> 项目 -> Python 解释器 -> 添加解释器 -> 添加本地解释器
   ![示例](https://imgur.com/QRo8O1C.png)
3. 点击 VirtualEnv -> 现有解释器 -> 选择您现有的 virtualenv 文件夹，如果您遵循默认安装，应该是 `evenv`。

   ![示例](https://imgur.com/XDmgjTw.png)

## 从新项目开始

如果您从头开始或想创建一个新的 Evennia 游戏，请使用此方法。
1. 点击新项目按钮。
2. 选择您的项目位置。您应该创建两个新文件夹，一个用于项目的根目录，一个用于直接存放 Evennia 游戏。它应该看起来像 `/location/projectfolder/gamefolder`。
3. 选择 `Custom environment` 解释器类型，使用 `Generate New` 类型为 `Virtual env`，使用与 https://www.evennia.com/docs/latest/Setup/Installation.html#requirements 中推荐的兼容基础 python 版本。然后选择一个文件夹作为项目文件夹的子文件夹来存放您的虚拟环境。

   ![新项目配置示例](https://imgur.com/R5Yr9I4.png)

点击创建按钮，它将带您进入一个基础虚拟环境的新项目。要安装 Evennia，您可以在项目文件夹中克隆 evennia 或通过 pip 安装。最简单的方法是使用 pip。

点击 `终端` 按钮

![终端按钮](https://i.imgur.com/fDr4nhv.png)

1. 输入 `pip install evennia`
2. 关闭 IDE 并导航到项目文件夹
3. 将游戏文件夹重命名为临时名称，并使用之前的名称创建一个新的空文件夹
4. 打开您的操作系统终端，导航到项目文件夹并激活您的 virtualenv。
   在 Linux 上，`source .evenv/bin/activate`
   在 Windows 上，`evenv\Scripts\activate`
5. 输入 `evennia --init mygame`
6. 将临时文件夹中的文件（应包含 `.idea/` 文件夹）移动到步骤 3 中创建的文件夹中，并删除现在为空的临时文件夹。
7. 在终端中，移动到文件夹并输入 `evennia migrate`
8. 启动 Evennia 以确保其正常工作，使用 `evennia start`，并使用 `evennia stop` 停止它

此时，您可以重新打开 IDE，并且它应该可以正常工作。[请在此处查看更多信息](https://www.evennia.com/docs/latest/Setup/Installation.html)

## 在 PyCharm 内调试 Evennia

### 附加到进程
1. 在 PyCharm 终端中启动 Evennia
2. 尝试启动两次，这将为您提供服务器的进程 ID
3. 在 PyCharm 菜单中，选择 `Run > Attach to Process...`
4. 从列表中选择相应的进程 ID，它应该是带有 `server.py` 参数的 `twistd` 进程（示例：`twistd.exe --nodaemon --logfile=\<mygame\>\server\logs\server.log --python=\<evennia repo\>\evennia\server\server.py`）

如果您想调试 Evennia 启动器或运行器，也可以附加到 `portal` 进程（或者只是了解它们如何工作！），请参阅下面的运行配置。

> 注意：每当您重新加载 Evennia 时，旧的服务器进程将终止并启动一个新的。因此，当您重新启动时，必须从旧进程分离，然后重新附加到新创建的进程。

### 使用运行/调试配置运行 Evennia

此配置允许您从 PyCharm 内启动 Evennia。除了方便之外，它还允许在更早的点暂停和调试 evennia_launcher 或 evennia_runner，而不是通过外部运行它们并附加。实际上，当服务器和/或门户正在运行时，启动器将已经退出。

#### 在 Windows 上
1. 转到 `Run > Edit Configutations...`
2. 点击加号以添加新配置并选择 Python
3. 添加脚本：`\<yourprojectfolder>\.evenv\Scripts\evennia_launcher.py`（如果您的 virtualenv 不叫 `evenv`，请替换）
4. 将脚本参数设置为：`start -l`（-l 启用控制台日志记录）
5. 确保选择的解释器是您的 virtualenv
6. 将工作目录设置为您的 `mygame` 文件夹（不是您的项目文件夹或 evennia）
7. 您可以参考 PyCharm 文档以获取一般信息，但您至少需要设置一个配置名称（如 "MyMUD start" 或类似名称）。

一个包含您新配置的下拉框应出现在您的 PyCharm 运行按钮旁边。选择它并按调试图标开始调试。

#### 在 Linux 上
1. 转到 `Run > Edit Configutations...`
2. 点击加号以添加新配置并选择 Python
3. 添加脚本：`/<yourprojectfolder>/.evenv/bin/twistd`（如果您的 virtualenv 不叫 `evenv`，请替换）
4. 将脚本参数设置为：`--python=/<yourprojectfolder>/.evenv/lib/python3.11/site-packages/evennia/server/server.py --logger=evennia.utils.logger.GetServerLogObserver --pidfile=/<yourprojectfolder>/<yourgamefolder>/server/server.pid --nodaemon`
5. 添加环境变量 `DJANGO_SETTINGS_MODULE=server.conf.settings`
6. 确保选择的解释器是您的 virtualenv
7. 将工作目录设置为您的游戏文件夹（不是您的项目文件夹或 evennia）
8. 您可以参考 PyCharm 文档以获取一般信息，但您至少需要设置一个配置名称（如 "MyMUD Server" 或类似名称）。

一个包含您新配置的下拉框应出现在您的 PyCharm 运行按钮旁边。选择它并按调试图标开始调试。请注意，这只启动服务器进程，您可以手动启动门户或为门户设置配置。步骤与上述非常相似。

1. 转到 `Run > Edit Configutations...`
2. 点击加号以添加新配置并选择 Python
3. 添加脚本：`/<yourprojectfolder>/.evenv/bin/twistd`（如果您的 virtualenv 不叫 `evenv`，请替换）
4. 将脚本参数设置为：`--python=/<yourprojectfolder>/.evenv/lib/python3.11/site-packages/evennia/server/portal/portal.py --logger=evennia.utils.logger.GetServerLogObserver --pidfile=/<yourprojectfolder>/<yourgamefolder>/server/portal.pid --nodaemon`
5. 添加环境变量 `DJANGO_SETTINGS_MODULE=server.conf.settings`
6. 确保选择的解释器是您的 virtualenv
7. 将工作目录设置为您的游戏文件夹（不是您的项目文件夹或 evennia）
8. 您可以参考 PyCharm 文档以获取一般信息，但您至少需要设置一个配置名称（如 "MyMUD Portal" 或类似名称）。

您现在应该能够启动这两种模式并获得完整的调试。如果您想更进一步，可以添加另一个配置以自动启动这两者。

1. 转到 `Run > Edit Configutations...`
2. 点击加号以添加新配置并选择 Compound
3. 添加您之前的两个配置，适当地命名并按确定。

您现在可以通过一次点击启动游戏，并激活完整的调试功能。
