# 使用 Docker 安装

Evennia 会在常规提交和发布时发布 [Docker 镜像](https://hub.docker.com/r/evennia/evennia/)，这使得在 Docker 容器中运行基于 Evennia 的游戏变得简单。

首先，安装 `docker` 程序以便运行 Evennia 容器。你可以从 [docker.com](https://www.docker.com/) 免费获取它。Linux 用户也可以通过他们的正常包管理器获取。

要获取最新的 Evennia Docker 镜像，运行：

```
docker pull evennia/evennia
```

这将获取最新的稳定镜像。

```
docker pull evennia/evennia:develop
```

获取基于 Evennia 不稳定 `develop` 分支的镜像。

接下来，`cd` 到你的游戏目录所在的位置，或者你想创建它的位置。然后运行：

```bash
docker run -it --rm -p 4000:4000 -p 4001:4001 -p 4002:4002 --rm -v $PWD:/usr/src/game --user $UID:$GID evennia/evennia
```

运行此命令后（见下一节的详细解释），你将处于 Docker 容器内的提示符下：

```bash
evennia|docker /usr/src/game $
```

这是一个普通的 shell 提示符。我们位于 Docker 容器内的 `/usr/src/game` 位置。如果你在开始时的文件夹中有任何内容，你应该可以在这里看到（使用 `ls`），因为我们将当前目录挂载到 `usr/src/game`（使用上面的 `-v`）。你可以使用 `evennia` 命令，并按照正常的[游戏设置](./Installation.md)说明创建新游戏（不需要虚拟环境）。

如果你愿意，可以从这个容器内部运行 Evennia，就像你在一个小型隔离的 Linux 环境中一样。要退出容器及其中的所有进程，请按 `Ctrl-D`。如果你创建了一个新的游戏文件夹，你会发现它已经出现在磁盘上。

> 从容器内部创建的游戏文件夹或任何新文件将显示为 `root` 所有。如果你想在容器外编辑这些文件，你应该更改所有权。在 Linux/Mac 上，你可以使用 `sudo chown myname:myname -R mygame`，其中 `myname` 替换为你的用户名，`mygame` 替换为你的游戏文件夹名称。

下面是我们使用的 `docker run` 命令的解释：

- `docker run ... evennia/evennia` 表示我们要基于 `evennia/evennia` Docker 镜像运行一个新容器。中间的所有内容都是该命令的选项。`evennia/evennia` 是我们在 dockerhub 仓库上的[官方 Docker 镜像](https://hub.docker.com/r/evennia/evennia/)的名称。如果你没有先运行 `docker pull evennia/evennia`，则在运行此命令时会下载镜像，否则将使用你已下载的版本。它包含运行 Evennia 所需的一切。
- `-it` 与在我们启动的容器内创建交互式会话有关。
- `--rm` 确保在容器关闭时删除它。这有助于保持磁盘整洁。
- `-p 4000:4000 -p 4001:4001 -p 4002:4002` 表示我们将 Docker 容器内的端口 `4000`、`4001` 和 `4002` 映射到主机上的同编号端口。这些是 telnet、web 服务器和 websockets 的端口。这使得你的 Evennia 服务器可以从容器外部访问（例如通过你的 MUD 客户端）！
- `-v $PWD:/usr/src/game` 将当前目录（*在容器外*）挂载到容器内的路径 `/usr/src/game`。这意味着当你在容器中编辑该路径时，你实际上是在修改硬盘上的“真实”位置。如果你没有这样做，任何更改只会存在于容器内，并在我们创建新容器时消失。请注意，在 Linux 中，当前目录的快捷方式是 `$PWD`。如果你的操作系统没有这个，你可以用当前磁盘目录的完整路径替换它（例如 `C:/Development/evennia/game` 或你希望你的 evennia 文件出现的任何地方）。
- `--user $UID:$GID` 确保容器对 `$PWD` 的修改是以你的用户和组 ID 而不是 root 的 ID 进行的（root 是在容器内运行 evennia 的用户）。这可以避免在容器重启之间在文件系统中留下陈旧的 `.pid` 文件，你必须在每次启动前使用 `sudo rm server/*.pid` 强制删除这些文件。

## 作为 Docker 镜像运行你的游戏

如果你从游戏目录运行前一节给出的 `docker` 命令，你可以轻松启动 Evennia 并在没有任何麻烦的情况下运行服务器。

除了安装方便之外，在容器中运行基于 Evennia 的游戏的主要好处是简化其在公共生产环境中的部署。如今，大多数基于云的托管提供商都支持运行基于容器的应用程序。这使得部署或更新你的游戏变得像在本地构建新容器镜像、将其推送到你的 Docker Hub 帐户，然后从 Docker Hub 拉取到你的 AWS/Azure/其他支持 Docker 的托管帐户一样简单。容器消除了安装 Python、设置虚拟环境或运行 pip 安装依赖项的需求。

### 通过 Docker 启动并运行 Evennia

对于远程或自动化部署，你可能希望在 Docker 容器启动时立即启动 Evennia。如果你已经有一个设置了数据库的游戏文件夹，你也可以启动 Docker 容器并直接传递命令。你传递的命令将是容器中运行的主要进程。从你的游戏目录运行，例如以下命令：

```
docker run -it --rm -p 4000:4000 -p 4001:4001 -p 4002:4002 --rm -v $PWD:/usr/src/game evennia/evennia evennia start -l
```

这将启动 Evennia 作为前台进程，将日志回显到终端。关闭终端将终止服务器。请注意，你*必须*使用前台命令，如 `evennia start -l` 或 `evennia ipstart` 来启动服务器，否则前台进程将立即完成，容器将关闭。

## 创建你自己的游戏镜像

这些步骤假设你已经创建或以其他方式获得了一个游戏目录。首先，`cd` 到你的游戏目录并创建一个名为 `Dockerfile` 的新空文本文件。将以下两行保存到其中：

```
FROM evennia/evennia:latest

ENTRYPOINT evennia start -l
```

这些是用于构建新 Docker 镜像的指令。这个镜像基于官方的 `evennia/evennia` 镜像，但也确保在运行时启动 evennia（这样我们就不需要进入它并运行命令）。

要构建镜像：

```bash
docker build -t mydhaccount/mygame .
```

（不要忘记最后的句点，它将使用当前位置的 `Dockerfile`）。这里的 `mydhaccount` 是你的 `dockerhub` 帐户的名称。如果你没有 dockerhub 帐户，你可以仅在本地构建镜像（在这种情况下可以随意命名容器，比如仅 `mygame`）。

Docker 镜像集中存储在你的计算机上。你可以通过 `docker images` 查看本地可用的镜像。一旦构建完成，你有几种选项来运行你的游戏。

### 从你的游戏镜像运行容器以进行开发

要在本地基于你的游戏镜像运行容器进行开发，请如前所述挂载本地游戏目录：

```
docker run -it --rm -p 4000:4000 -p 4001:4001 -p 4002:4002 -v $PWD:/usr/src/game --user $UID:$GID mydhaccount/mygame
```

Evennia 将启动并在终端中输出，非常适合开发。你应该可以正常连接到游戏。

### 部署游戏镜像以进行生产

每次按照上述说明重建 Docker 镜像时，游戏目录的最新副本实际上会被复制到镜像内部（在 `/usr/src/game/`）。如果你不在此处挂载磁盘上的文件夹，将使用内部文件夹。因此，要在服务器上部署 evennia，请省略 `-v` 选项，只需给出以下命令：

```
docker run -it --rm -d -p 4000:4000 -p 4001:4001 -p 4002:4002 --user $UID:$GID mydhaccount/mygame
```

你的游戏将从你的 docker-hub 帐户下载，并使用镜像构建一个新容器并在服务器上启动！如果你的服务器环境强制你使用不同的端口，你可以在上面的命令中以不同方式映射正常端口。

上面我们添加了 `-d` 选项，这会以*守护进程*模式启动容器——你不会在控制台中看到任何返回。你可以使用 `docker ps` 查看它正在运行：

```bash
$ docker ps

CONTAINER ID     IMAGE       COMMAND                  CREATED              ...
f6d4ca9b2b22     mygame      "/bin/sh -c 'evenn..."   About a minute ago   ...
```

注意容器 ID，这是你在运行时管理容器的方式。

```
docker logs f6d4ca9b2b22
```
查看容器的标准输出（即正常的服务器日志）
```
docker logs -f f6d4ca9b2b22
```
跟踪日志（使其“实时”更新到屏幕）。
```
docker pause f6d4ca9b2b22
```
暂停容器的状态。
```
docker unpause f6d4ca9b2b22
```
在暂停后重新启用。它将从暂停的地方继续。
```
docker stop f6d4ca9b2b22
```
停止容器。要再次启动它，你需要使用 `docker run`，指定端口等。新容器将获得一个新的容器 ID 以供引用。

## 工作原理

`evennia/evennia` Docker 镜像包含 Evennia 库及其所有依赖项。它还具有一个 `ONBUILD` 指令，该指令在从其派生的镜像构建过程中触发。此 `ONBUILD` 指令处理设置卷并将你的游戏目录代码复制到容器内的正确位置。

在大多数情况下，基于 Evennia 的游戏的 Dockerfile 只需要 `FROM evennia/evennia:latest` 指令，如果你计划在 Docker Hub 上发布镜像并希望提供联系信息，则可以选择添加 `MAINTAINER` 指令。

有关 Dockerfile 指令的更多信息，请参阅 [Dockerfile 参考](https://docs.docker.com/engine/reference/builder/)。

有关卷和 Docker 容器的更多信息，请参阅 Docker 网站的[管理容器中的数据](https://docs.docker.com/engine/tutorials/dockervolumes/)页面。

### 如果我不想要“LATEST”怎么办？

每当 Evennia 的 `main` 分支有新提交时，都会自动构建一个新的 `evennia/evennia` 镜像。可以基于任何任意提交创建你自己的自定义 Evennia 基础 Docker 镜像。

1. 使用 git 工具检出你想要基于其构建镜像的提交。（在下面的示例中，我们正在检出提交 a8oc3d5b。）

```
git checkout -b my-stable-branch a8oc3d5b
```

2. 将工作目录更改为包含 `Dockerfile` 的 `evennia` 目录。请注意，`Dockerfile` 随时间变化，因此如果你要回到提交历史的较早位置，可能需要带上最新的 `Dockerfile` 副本，并使用它代替当时使用的版本。

3. 使用 `docker build` 命令基于当前检出的提交构建镜像。下面的示例假设你的 Docker 帐户是 **mydhaccount**。

```
docker build -t mydhaccount/evennia .
```

4. 现在你有一个基于特定提交构建的 Evennia 基础 Docker 镜像。要使用此镜像构建游戏，你需要修改游戏目录的 **Dockerfile** 中的 **FROM** 指令为：

```
FROM mydhacct/evennia:latest
```

注意：从这一点开始，你还可以使用 `docker tag` 命令为你的镜像设置特定标签，并/或将其上传到 Docker Hub 下的帐户。

5. 此时，使用与往常相同的 `docker build` 命令构建你的游戏。将工作目录更改为你的游戏目录并运行

```
docker build -t mydhaccount/mygame .
```

## 额外的便利

Docker 生态系统包括一个名为 `docker-compose` 的工具，可以协调复杂的多容器应用程序，或者在我们的情况下，存储我们每次运行容器时希望指定的默认端口和终端参数。用于在开发中运行容器化 Evennia 游戏的示例 `docker-compose.yml` 文件可能如下所示：

```
version: '2'

services:
  evennia:
    image: mydhacct/mygame
    stdin_open: true
    tty: true
    ports:
      - "4001-4002:4001-4002"
      - "4000:4000"
    volumes: 
      - .:/usr/src/game
```

将此文件放在游戏目录中的 `Dockerfile` 旁边，启动容器就像

```
docker-compose up
```

有关 `docker-compose` 的更多信息，请参阅[使用 docker-compose 入门](https://docs.docker.com/compose/gettingstarted/)。

> 请注意，使用此设置会失去 `--user $UID` 选项。问题是变量 `UID` 在配置文件 `docker-compose.yml` 中不可用。解决方法是在其中硬编码你的用户和组 ID。在终端中运行 `echo $UID:$GID`，如果例如你得到 `1000:1000`，你可以在 `docker-compose.yml` 的 `image: ...` 行下方添加一行 `user: 1000:1000`。
