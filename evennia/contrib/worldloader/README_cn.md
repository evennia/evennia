# 简介
这是Evennia(http://github.com/evennia/evennia)的工具，可以从CSV文件加载游戏世界。


## 安装
你需要先安装Evennia并且创建你的游戏。Evennia的文档可见这里：http://github.com/evennia/evennia/wiki 。

将文件夹```/example_tutorial_world/worlddata```复制到你的游戏目录中。目录结构应该像以下这样：

```
game
  |
  ----- commands  
    |
    --- server
    |
    --- ...
    |
    --- worlddata
```

将以下内容添加到```/server/conf/settings.py```的末尾：
```
from worlddata import world_settings
INSTALLED_APPS = INSTALLED_APPS + (world_settings.WORLD_DATA_APP,)
```

执行```evennia migrate```。
  
将以下内容添加到```/commands/default_cmdsets.py```的开头:
```
import evennia.contrib.worldloader.command as loadercmd
```

将以下内容添加到```/commands/default_cmdsets.py```的```CharacterCmdSet```的 ```at_cmdset_creation```中：

```
        self.add(loadercmd.CmdImportCsv())
        self.add(loadercmd.CmdBatchBuilder())
        self.add(loadercmd.CmdSetDataInfo())
```

```/commands/default_cmdsets.py```看上去应该像这样：
```
from evennia import default_cmds
import evennia.contrib.worldloader.command as loadercmd

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `PlayerCmdSet` when a Player puppets a Character.
    """
    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super(CharacterCmdSet, self).at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #

        self.add(loadercmd.CmdImportCsv())
        self.add(loadercmd.CmdBatchBuilder())
        self.add(loadercmd.CmdSetDataInfo())
```

这添加了三个新命令：

1. ```@importcsv``` 它可以从CSV文件导入数据到游戏数据库。CSV文件的路径在```/worlddata/world_settings.py```的```CSV_DATA_FOLDER```中定义。

2. ```@datainfo``` 它可以在游戏中直接设置物体的数据信息。

3. ```@batchbuild``` 它可以通过CSV文件中的数据构建整个游戏世界。

在```worlddata/world_settings.py```中你可以通过```CSV_DATA_FOLDER```设定CSV文件所在的文件夹。



## CSV数据文件
CSV文件（除了```world_details.csv```）具有以下字段：
```
key,name,alias,typeclass,desc,lock,attributes,location,destination
```

这些值用于设置物体的相应属性。```attributes```字段中的数据必须是Python的字典。除上述字段之外的其他字段都会设置为物体的属性。

```world_rooms.csv```、```world_exits.csv```、```world_objects.csv```中的物体是唯一的，每一条记录会对应世界中的一个且只有一个物体。

```personal_objects.csv```中的物体是不唯一的，每一条记录可以对应零个之多个物体。

```world_details.csv```用于记录物体的detail信息。

```key```字段中的数据必须是全局唯一的，加载程序用它来识别物体，```location```和```destination```字段也使用这些```key```。



## 安装世界教程
该世界教程源自Evennia的世界教程。

启动Evennia并且登录进游戏。

作为游戏中的建造者，你需要将自己移动到Limbo然后执行：
```
@datainfo #2=limbo
```
（这会给Limbo添加一个唯一的键。）

然后输入：
```
@batchbld
```

如果一切正常，世界教程会安装好。



## 使用其他的世界
如果你想要使用其他的世界，你可以将```worlddata/world_settings.py```中的```CSV_DATA_FOLDER```设置到你的游戏世界数据的文件夹。

```
CSV_DATA_FOLDER = "worlddata/your_world"
```

然后在你的游戏中执行```@batchbld```。
