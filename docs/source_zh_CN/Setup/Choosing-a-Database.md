# 选择数据库

本页面概述了支持的 SQL 数据库以及安装说明：

- SQLite3（默认）
- PostgreSQL
- MySQL / MariaDB

由于 Evennia 使用 [Django](https://djangoproject.com)，大部分信息基于社区和他们的文档。虽然以下信息可能有用，但你可以在 Django 的[支持数据库说明](https://docs.djangoproject.com/en/4.1/ref/databases/#ref-databases)页面找到最新和“正确”的信息。

## SQLite3（默认）

[SQLite3](https://sqlite.org/) 是一个轻量级的单文件数据库。它是我们的默认数据库，如果没有其他选项，Evennia 会自动为你设置这个。

SQLite 将数据库存储在一个文件中（`mygame/server/evennia.db3`）。这意味着重置数据库非常简单——只需删除（或移动）该 `evennia.db3` 文件，然后再次运行 `evennia migrate`！不需要服务器进程，管理开销和资源消耗极小。由于在内存中运行，它也非常快。对于绝大多数 Evennia 安装，这可能就是所需的一切。

SQLite 通常比 MySQL/PostgreSQL 快得多，但其性能有两个缺点：

- SQLite [设计上忽略长度限制](https://www.sqlite.org/faq.html#q9)；可以在技术上不接受的字段中存储非常大的字符串和数字。这不会引起注意；你的游戏会正常读写它们，但如果你需要更改数据库，这可能会导致一些数据迁移问题。
- SQLite 可以很好地扩展到存储数百万个对象，但如果大量用户同时访问你的 MUD 和网站，或者你发现自己在实时游戏中编写长时间运行的函数来更新大量对象，都会产生错误和干扰。SQLite 无法可靠地处理多个并发线程或进程访问其记录。这与数据库文件的文件锁定冲突有关。因此，对于大量使用进程或线程池的生产服务器，更合适的选择是使用合适的数据库。

### 安装 SQLite3

这作为 Evennia 的一部分安装和配置。当你运行以下命令时，数据库文件将创建为 `mygame/server/evennia.db3`：

```bash
evennia migrate
```

不更改任何数据库选项。一个可选要求是 `sqlite3` 客户端程序——如果你想手动检查数据库数据，这是必需的。使用 Evennia 数据库的快捷方式是 `evennia dbshell`。Linux 用户应查找其发行版的 `sqlite3` 软件包，而 Mac/Windows 用户应从[此页面](https://sqlite.org/download.html)获取 sqlite-tools 包。

要检查默认的 Evennia 数据库（创建后），请进入你的游戏目录并执行：

```bash
sqlite3 server/evennia.db3
# 或者
evennia dbshell
```

这将带你进入 sqlite 命令行。使用 `.help` 获取说明，使用 `.quit` 退出。有关命令的速查表，请参见[此处](https://gist.github.com/vincent178/10889334)。

### 重置 SQLite3

如果你想重置 SQLite3 数据库，请参见[此处](./Updating-Evennia.md#sqlite3-default)。

## PostgreSQL

[PostgreSQL](https://www.postgresql.org/) 是一个开源数据库引擎，Django 推荐使用。虽然在正常使用情况下不如 SQLite 快，但如果你的游戏有非常大的数据库和/或通过单独的服务器进程进行广泛的网络展示，它将比 SQLite 更好地扩展。

### 安装和初始设置 PostgreSQL

首先，安装 posgresql 服务器。版本 `9.6` 已通过 Evennia 测试。所有发行版都可以轻松获取软件包。你还需要获取 `psql` 客户端（在基于 debian 的系统上称为 `postgresql-client`）。Windows/Mac 用户可以在 [postgresql 下载页面](https://www.postgresql.org/download/)找到所需内容。安装时应为数据库超级用户（始终称为 `postgres`）设置密码。

要与 Evennia 交互，还需要在你的 Evennia 安装中安装 `psycopg2`（在你的虚拟环境中使用 `pip install psycopg2-binary`）。这充当与数据库服务器的 Python 桥梁。

接下来，启动 postgres 客户端：

```bash
psql -U postgres --password
```

```{warning}
使用 `--password` 参数时，Postgres 应提示你输入密码。如果没有，请用 `-p yourpassword` 替换。除非必要，否则不要使用 `-p` 参数，因为结果命令和你的密码将记录在 shell 历史中。
```

这将使用 psql 客户端打开一个到 postgres 服务的控制台。

在 psql 命令行上：

```sql
CREATE USER evennia WITH PASSWORD 'somepassword';
CREATE DATABASE evennia;

-- Postgres 特定的优化
-- https://docs.djangoproject.com/en/dev/ref/databases/#optimizing-postgresql-s-configuration
ALTER ROLE evennia SET client_encoding TO 'utf8';
ALTER ROLE evennia SET default_transaction_isolation TO 'read committed';
ALTER ROLE evennia SET timezone TO 'UTC';

GRANT ALL PRIVILEGES ON DATABASE evennia TO evennia;
-- 对于 Postgres 10+
ALTER DATABASE evennia owner to evennia;

-- 其他有用的命令：
--  \l       （列出所有数据库和权限）
--  \q       （退出）
```

[这里](https://gist.github.com/Kartones/dd3ff5ec5ea238d4c546)是 psql 命令的速查表。

我们创建了一个数据库用户 'evennia' 和一个新数据库 `evennia`（你可以随意命名）。然后我们授予 'evennia' 用户对新数据库的完全权限，以便它可以读写等。如果将来想要完全清空数据库，可以再次以 `postgres` 超级用户身份登录，然后执行 `DROP DATABASE evennia;`，然后再次执行上面的 `CREATE` 和 `GRANT` 步骤以重新创建数据库并授予权限。

### Evennia PostgreSQL 配置

编辑 `mygame/server/conf/secret_settings.py` 并添加以下部分：

```python
#
# PostgreSQL 数据库配置
#
DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'evennia',
            'USER': 'evennia',
            'PASSWORD': 'somepassword',
            'HOST': 'localhost',
            'PORT': ''    # 使用默认端口
        }}
```

如果你为数据库和用户使用了其他名称，请输入那些名称。运行

```bash
evennia migrate
```

以填充你的数据库。如果你想直接检查数据库，从现在开始也可以使用

```bash
evennia dbshell
```

作为进入正确数据库和用户的 postgres 命令行的快捷方式。

设置数据库后，现在应该能够使用新数据库正常启动 Evennia。

### 重置 PostgreSQL

如果你想重置 PostgreSQL 数据库，请参见[此处](./Updating-Evennia.md#postgresql)。

### 高级 PostgreSQL 使用（远程服务器）

```{warning}
下面的示例适用于不开放互联网的私人网络中的服务器。在对互联网可访问的服务器进行任何更改之前，请确保了解详细信息。
```

上述讨论适用于托管本地服务器。在某些配置中，可能需要将数据库托管在 Evennia 运行的服务器之外的服务器上。一个示例情况是代码开发可能由多个用户在多台机器上进行。在此配置中，本地数据库（如 SQLite3）不可行，因为所有机器和开发人员都无法访问该文件。

选择一台远程机器来托管数据库和 PostgreSQL 服务器。在该服务器上按照[上述说明](#install-and-initial-setup-of-postgresql)设置数据库。根据发行版，PostgreSQL 只接受本地机器（localhost）上的连接。为了启用远程访问，需要更改两个文件。

首先，确定哪个集群正在运行你的数据库。使用 `pg_lscluster`：

```bash
$ pg_lsclusters
Ver Cluster Port Status Owner    Data directory              Log file
12  main    5432 online postgres /var/lib/postgresql/12/main /var/log/postgresql/postgresql-12-main.log
```

接下来，编辑数据库的 `postgresql.conf`。在 Ubuntu 系统上，这个文件位于 `/etc/postgresql/<ver>/<cluster>`，其中 `<ver>` 和 `<cluster>` 是 `pg_lscluster` 输出中报告的内容。因此，对于上述示例，文件是 `/etc/postgresql/12/main/postgresql.conf`。

在此文件中，查找包含 `listen_addresses` 的行。例如：

```
listen_address = 'localhost'    # 监听的 IP 地址；
                                # 逗号分隔的地址列表；
                                # 默认为 'localhost'；使用 '*' 表示所有
```

```{warning}
错误配置错误的集群可能会导致现有集群出现问题。
```

还要注意包含 `port =` 的行，并记住端口号。

将 `listen_addresses` 设置为 `'*'`。这允许 postgresql 接受任何接口上的连接。

```{warning}
将 `listen_addresses` 设置为 `'*'` 会在所有接口上打开一个端口。如果你的服务器可以访问互联网，请确保你的防火墙配置适当，以根据需要限制对此端口的访问。（你也可以列出要监听的显式地址和子网。有关详细信息，请参阅 postgresql 文档。）
```

最后，修改 `pg_hba.conf`（与 `postgresql.conf` 位于同一目录中）。查找包含以下内容的行：

```
# IPv4 本地连接：
host    all             all             127.0.0.1/32            md5
```

添加以下行：

```
host    all             all             0.0.0.0/0               md5
```

```{warning}
这允许来自*所有* IP 的传入连接。请参阅 PosgreSQL 文档以了解如何限制此连接。
```

现在，重新启动你的集群：

```bash
$ pg_ctlcluster 12 main restart
```

最后，更新 Evennia secret_settings.py 中的数据库设置（如[上述说明](#evennia-postgresql-configuration)所述），修改 `SERVER` 和 `PORT` 以匹配你的服务器。

现在你的 Evennia 安装应该能够连接并与远程服务器通信。

## MySQL / MariaDB

[MySQL](https://www.mysql.com/) 是一个常用的专有数据库系统，与 PostgreSQL 相当。有一个开源替代品称为 [MariaDB](https://mariadb.org/)，它模仿前者的所有功能和命令语法。因此，本节涵盖两者。

### 安装和初始设置 MySQL/MariaDB

首先，为你的特定服务器安装和设置 MariaDB 或 MySQL。Linux 用户应查找其发行版的 `mysql-server` 或 `mariadb-server` 软件包。Windows/Mac 用户可以在 [MySQL 下载页面](https://www.mysql.com/downloads/)或 [MariaDB 下载页面](https://mariadb.org/download/)找到所需内容。你还需要相应的数据库客户端（`mysql`，`mariadb-client`），以便设置数据库本身。安装服务器时，通常会要求你设置数据库根用户和密码。

最后，你还需要一个 Python 接口，以允许 Evennia 与数据库通信。Django 推荐使用 `mysqlclient`。在 Evennia 虚拟环境中使用 `pip install mysqlclient` 安装它。

启动数据库客户端（对于 mysql 和 mariadb，名称相同）：

```bash
mysql -u root -p
```

你应该输入数据库根密码（在安装数据库服务器时设置）。

在数据库客户端界面中：

```sql
CREATE USER 'evennia'@'localhost' IDENTIFIED BY 'somepassword';
CREATE DATABASE evennia;
ALTER DATABASE `evennia` CHARACTER SET utf8; -- 注意是 `evennia` 用反引号，不是引号！
GRANT ALL PRIVILEGES ON evennia.* TO 'evennia'@'localhost';
FLUSH PRIVILEGES;
-- 使用 'exit' 退出客户端
```

[这里](https://gist.github.com/hofmannsven/9164408)是 mysql 命令的速查表。

在上面，我们创建了一个新的本地用户和数据库（我们在这里将两者都命名为 'evennia'，你可以随意命名）。我们将字符集设置为 `utf8`，以避免在某些安装中可能出现的前缀字符长度问题。接下来，我们授予 'evennia' 用户对 `evennia` 数据库的所有权限，并确保应用权限。退出客户端将我们带回正常的终端/控制台。

> 如果你没有将 MySQL 用于其他任何用途，可以考虑通过 `GRANT ALL PRIVILEGES ON *.* TO 'evennia'@'localhost';` 授予 'evennia' 用户完全权限。如果这样做，意味着你可以稍后使用 `evennia dbshell` 连接到 mysql，删除你的数据库并重新创建它，作为一种简单的重置方式。没有此额外权限，你将能够删除数据库，但不能在不首先切换到数据库根用户的情况下重新创建它。

### 将 MySQL/MariaDB 配置添加到 Evennia

要告诉 Evennia 使用你的新数据库，你需要编辑 `mygame/server/conf/settings.py`（或 `secret_settings.py`，如果你不希望你的数据库信息在 git 仓库中传递）。

> Django 文档建议使用外部 `db.cnf` 或其他外部 conf 格式文件。然而，Evennia 用户发现这会导致问题（参见例如 [issue #1184](https://git.io/vQdiN)）。为了避免麻烦，我们建议你简单地将配置放在你的设置中，如下所示。

```python
    #
    # MySQL 数据库配置
    #
    DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.mysql',
           'NAME': 'evennia',
           'USER': 'evennia',
           'PASSWORD': 'somepassword',
           'HOST': 'localhost',  # 或你的数据库托管的 IP 地址
           'PORT': '', # 使用默认端口
       }
    }
```

`MariaDB` 也使用 `mysql` 后端。

根据你的数据库设置进行更改。接下来，运行：

```bash
evennia migrate
```

以填充你的数据库。如果你想直接检查数据库，从现在开始也可以使用

```bash
evennia dbshell
```

作为进入 postgres 命令行的快捷方式，用于正确的数据库和用户。

设置数据库后，现在应该能够使用新数据库正常启动 Evennia。

### 重置 MySQL/MariaDB

如果你想重置 MySQL/MariaDB 数据库，请参见[此处](./Updating-Evennia.md#mysql-mariadb)。

## 其他数据库

尚未对 Oracle 进行测试，但它也通过 Django 支持。有社区维护的 [MS SQL](https://code.google.com/p/django-mssql/) 驱动程序，可能还有其他一些。如果你尝试其他数据库，请考虑为本页面贡献说明。
