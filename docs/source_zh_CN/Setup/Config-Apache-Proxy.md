# 配置 Apache 代理

Evennia 自带一个 Web 服务器，通常不需要替换。但使用像 Apache 这样的外部 Web 服务器作为 Evennia Web 服务器前的*代理*可能是另一个原因。要实现 TLS（加密）需要一些额外的工作，本文最后会介绍。

```{warning} 可能已过时
以下的 Apache 指南可能已过时。如果某些内容无法正常工作，或者你使用 Evennia 搭配不同的服务器，请告知我们。
```

## 在 Evennia 前运行 Apache 作为代理

以下是使用前端代理（Apache HTTP）、`mod_proxy_http`、`mod_proxy_wstunnel` 和 `mod_ssl` 运行 Evennia 的步骤。`mod_proxy_http` 和 `mod_proxy_wstunnel` 将在下文中简称为 `mod_proxy`。

### 安装 `mod_ssl`

- *Fedora/RHEL* - Apache HTTP 服务器和 `mod_ssl` 可以在 Fedora 和 RHEL 的标准软件包库中找到：
    ```
    $ dnf install httpd mod_ssl
    或
    $ yum install httpd mod_ssl
    ```
- *Ubuntu/Debian* - Apache HTTP 服务器和 `mod_ssl` 在 Ubuntu 和 Debian 的 `apache2` 软件包中安装，并在标准软件包库中可用。安装后需要启用 `mod_ssl`：
    ```
    $ apt-get update
    $ apt-get install apache2 
    $ a2enmod ssl
    ```

### TLS 代理+WebSocket 配置

下面是一个启用 TLS 的 HTTP 和 WebSocket 代理的 Evennia 示例配置。

#### Apache HTTP 服务器配置

```
<VirtualHost *:80>
  # 始终重定向到 https/443
  ServerName mud.example.com
  Redirect / https://mud.example.com
</VirtualHost>

<VirtualHost *:443>
  ServerName mud.example.com
  
  SSLEngine On
  
  # 证书和密钥的位置
  SSLCertificateFile /etc/pki/tls/certs/mud.example.com.crt
  SSLCertificateKeyFile /etc/pki/tls/private/mud.example.com.key
  
  # 使用工具 https://www.ssllabs.com/ssltest/ 在设置后扫描你的设置。
  SSLProtocol TLSv1.2
  SSLCipherSuite HIGH:!eNULL:!NULL:!aNULL
  
  # 将所有 WebSocket 流量代理到 Evennia 的 4002 端口
  ProxyPass /ws ws://127.0.0.1:4002/
  ProxyPassReverse /ws ws://127.0.0.1:4002/
  
  # 将所有 HTTP 流量代理到 Evennia 的 4001 端口
  ProxyPass / http://127.0.0.1:4001/
  ProxyPassReverse / http://127.0.0.1:4001/
  
  # 为此 Evennia 代理配置单独的日志记录
  ErrorLog logs/evennia_error.log
  CustomLog logs/evennia_access.log combined
</VirtualHost>
```

#### Evennia 安全 WebSocket 配置

在设置 Evennia 时需要稍作调整，以便代理正确处理 WebSocket 流量。你必须在 `mymud/server/conf/settings.py` 文件中设置 `WEBSOCKET_CLIENT_URL`：

```
WEBSOCKET_CLIENT_URL = "wss://external.example.com/ws"
```

上述设置是客户端浏览器实际使用的。注意使用 `wss://` 是因为我们的客户端将通过加密连接进行通信（"wss" 表示 SSL/TLS 上的 WebSocket）。特别注意 URL 末尾的附加路径 `/ws`。这就是 Apache HTTP 服务器识别特定请求应被代理到 Evennia 的 WebSocket 端口的方式，但这也适用于其他类型的代理（如 nginx）。

## 使用 Apache 替代 Evennia Web 服务器

```{warning} 不支持，也不推荐。
这是因为有人询问过才涉及。Web 客户端将无法工作。它也会在进程外运行，导致竞争条件。这不直接支持，所以如果你尝试这样做，你需要自行解决。
```

### 安装 `mod_wsgi`

- *Fedora/RHEL* - Apache HTTP 服务器和 `mod_wsgi` 可以在 Fedora 和 RHEL 的标准软件包库中找到：
    ```
    $ dnf install httpd mod_wsgi
    或
    $ yum install httpd mod_wsgi
    ```
- *Ubuntu/Debian* - Apache HTTP 服务器和 `mod_wsgi` 可以在 Ubuntu 和 Debian 的标准软件包库中找到：
   ```
   $ apt-get update
   $ apt-get install apache2 libapache2-mod-wsgi
   ```

### 复制并修改 VHOST

安装 `mod_wsgi` 后，将 `evennia/web/utils/evennia_wsgi_apache.conf` 文件复制到你的 apache2 vhosts/sites 文件夹。在 Debian/Ubuntu 上，这是 `/etc/apache2/sites-enabled/`。请在复制文件后进行修改。

阅读注释并更改路径以指向你设置中的适当位置。

### 重启/重新加载 Apache

更改配置后，你需要重新加载或重启 apache2。

- *Fedora/RHEL/Ubuntu*
    ```
    $ systemctl restart httpd
    ```
- *Ubuntu/Debian*
    ```
    $ systemctl restart apache2
    ```

如果一切顺利，你将能够在浏览器中指向你在 vhost 中设置的域或子域，并看到漂亮的默认 Evennia 网页。如果没有，请阅读希望有用的错误信息并从那里开始解决问题。问题可以向我们的 [Evennia 社区网站](https://evennia.com) 提出。

### 关于代码重载的说明

如果你的 `mod_wsgi` 设置为在守护模式下运行（在 Debian 和 Ubuntu 上默认如此），你可以使用 `touch` 命令来告诉 `mod_wsgi` 重新加载 `evennia/game/web/utils/apache_wsgi.conf`。当 `mod_wsgi` 看到文件修改时间发生变化时，它将强制代码重新加载。任何代码的修改都不会传播到你网站的实时实例，直到重新加载。

如果你没有在守护模式下运行或想强制执行，只需重启或重新加载 apache2 以应用更改。

### 进一步的注意事项和提示：

如果你从 Apache 收到奇怪的（通常是无信息的）`Permission denied` 错误，请确保你的 `evennia` 目录位于 Web 服务器实际上可以访问的位置。例如，某些 Linux 发行版可能默认对用户的 `/home` 目录设置非常严格的访问权限。

有用户评论说，他们必须在 Apache 配置中添加以下内容才能正常工作。未确认，但如果有问题，值得尝试。

```apache
<Directory "/home/<yourname>/evennia/game/web">
    Options +ExecCGI
    Allow from all
</Directory>
```
