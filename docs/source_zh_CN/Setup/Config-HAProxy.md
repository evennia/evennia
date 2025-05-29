# 配置 HAProxy

如今，一个面向公众的网站应该通过加密连接提供服务。因此，网站应使用 `https:` 而不是 `http:`，Web 客户端使用的 WebSocket 连接应使用 `wss:` 而不是 `ws:`。

原因在于安全性——不仅可以确保用户访问的是正确的网站（而不是劫持原地址的假冒网站），还可以防止恶意中间人窥探传输中的数据（如密码）。

Evennia 本身不实现 https/wss 连接。这最好由能够跟上最新安全实践的专用工具来处理。

因此，我们将在 Evennia 和服务器的外部端口之间安装一个*代理*。基本上，Evennia 会认为它只在本地（localhost，IP 127.0.0.1）运行，而代理会透明地将其映射到“真实”的外部端口，并为我们处理 HTTPS/WSS。

```
             Evennia
                |
    (仅内部的本地 IP/端口提供 HTTP/WS)
                |
              Proxy
                |
    (外部可见的公共 IP/端口提供 HTTPS/WSS)
                |
             Firewall
                |
             Internet
```

这些说明假设你运行的是 Unix/Linux 服务器（如果你使用远程托管，这很常见），并且你对该服务器有 root 访问权限。

我们需要的组件：

- [HAProxy](https://www.haproxy.org/) - 一个易于设置和使用的开源代理程序。
- [LetsEncrypt](https://letsencrypt.org/getting-started/) 提供建立加密连接所需的用户证书。特别是我们将使用优秀的 [Certbot](https://certbot.eff.org/instructions) 程序，它自动化了使用 LetsEncrypt 的整个证书设置过程。
- `cron` - 所有 Linux/Unix 系统都自带的工具，用于在操作系统中自动化任务。

在开始之前，你还需要以下信息和设置：

- （可选）你的游戏的主机名。这是你必须从_域名注册商_处购买并通过 DNS 设置指向服务器 IP 的内容。为了本手册的方便，我们假设你的主机名是 `my.awesomegame.com`。
- 如果你没有域名或尚未设置它，你至少必须知道服务器的 IP 地址。可以通过在服务器内部使用 `ifconfig` 或类似工具找到。如果你使用像 DigitalOcean 这样的托管服务，你也可以在控制面板中找到虚拟机的 IP 地址。在所有地方使用这个作为主机名。
- 你必须在防火墙中打开端口 80。Certbot 在下面用于自动续订证书。因此，在不进行调整的情况下，你不能在此设置旁边运行另一个 Web 服务器。
- 你必须在防火墙中打开端口 443（HTTPS）。这将是外部 Web 服务器端口。
- 确保防火墙中未打开端口 4001（内部 Web 服务器端口）（除非你之前明确打开了它，否则通常会默认关闭）。
- 在防火墙中打开端口 4002（我们将为内部和外部端口使用相同的号码，代理只会显示提供 wss 的安全端口）。

## 获取证书

证书保证你的身份。最简单的方法是使用 [Letsencrypt](https://letsencrypt.org/getting-started/) 和 [Certbot](https://certbot.eff.org/instructions) 程序获取。Certbot 为各种操作系统提供了很多安装说明。以下是适用于 Debian/Ubuntu 的说明：

```bash
sudo apt install certbot
```

确保停止 Evennia 并且没有使用端口 80 的服务正在运行，然后执行：

```bash
sudo certbot certonly --standalone
```

你将需要回答一些问题，例如用于发送证书错误的电子邮件和用于此证书的主机名（或 IP，假设）。完成后，证书将位于 `/etc/letsencrypt/live/<yourhostname>/*pem`（Ubuntu 示例）。对于我们的目的，关键文件是 `fullchain.pem` 和 `privkey.pem`。

Certbot 设置了一个 cron-job/systemd 任务来定期续订证书。要检查这是否有效，请尝试：

```bash
sudo certbot renew --dry-run
```

证书的有效期仅为 3 个月，因此请确保此测试有效（它需要端口 80 打开）。请查看 Certbot 的页面以获取更多帮助。

我们还没有完全完成。HAProxy 期望这两个文件是一个文件。更具体地说，我们将：
1. 复制 `privkey.pem` 并将其复制到一个名为 `<yourhostname>.pem`（例如 `my.awesomegame.com.pem`）的新文件中。
2. 将 `fullchain.pem` 的内容附加到此新文件的末尾。不需要空行。

我们可以通过在文本编辑器中复制粘贴来完成此操作，但这里是如何使用 shell 命令完成的（用你自己的路径替换示例路径）：

```bash
cd /etc/letsencrypt/live/my.awesomegame.com/
sudo cp privkey.pem my.awesomegame.com.pem
sudo cat fullchain.pem >> my.awesomegame.com.pem
```

新的 `my.awesomegame.com.pem` 文件（或你命名的任何文件）就是我们将在下面的 HAProxy 配置中指向的文件。

这里有一个问题 - Certbot 会在 3 个月的证书到期前几天自动为我们生成 `fullchain.pem`。但 HAProxy 不会看到这一点，因为它正在查看的合并文件仍然附加了旧的 `fullchain.pem`。

我们将通过使用 Unix/Linux 的 `cron` 程序定期重建 `.pem` 文件来设置自动化任务。

```bash
crontab -e
```

编辑器将打开 crontab 文件。在底部添加以下内容（全部在一行上，并将路径更改为你自己的）：

```bash
0 5 * * * cd /etc/letsencrypt/live/my.awesomegame.com/ &&
    cp privkey.pem my.awesomegame.com.pem &&
    cat fullchain.pem >> my.awesomegame.com.pem
```

保存并关闭编辑器。现在，每天晚上 05:00（凌晨 5 点），`my.awesomegame.com.pem` 将为你重建。由于 Certbot 会在证书到期前几天更新 `fullchain.pem` 文件，这应该有足够的时间确保 HaProxy 不会看到过期的证书。

## 安装和配置 HAProxy

安装 HaProxy 通常很简单：

```bash
# Debian 衍生版本（Ubuntu、Mint 等）
sudo apt install haproxy

# Redhat 衍生版本（对于非常新的 Fedora 发行版，使用 dnf 而不是 yum）
sudo yum install haproxy
```

HAProxy 的配置在一个文件中完成。这个文件可以放在你喜欢的任何地方，现在放在你的游戏目录中并命名为 `haproxy.cfg`。

这是在 Centos7 和 Ubuntu 上测试的示例。确保更改文件以输入你自己的值。

我们在这里使用 `my.awesomegame.com` 示例，以下是端口：

- `443` 是标准的 SSL 端口
- `4001` 是标准的 Evennia Web 服务器端口（防火墙关闭！）
- `4002` 是默认的 Evennia WebSocket 端口（我们为外发的 wss 端口使用相同的号码，因此防火墙中应该打开此端口）。

```shell
# 设置 haproxy 的基本配置
global
    log /dev/log local0
    chroot /var/lib/haproxy
    maxconn  4000
    user  haproxy
    tune.ssl.default-dh-param 2048
    ## 当一切正常时取消注释此行
    # daemon
defaults
    mode http
    option forwardfor

# Evennia 具体配置
listen evennia-https-website
    bind my.awesomegame.com:443 ssl no-sslv3 no-tlsv10 crt /etc/letsencrypt/live/my.awesomegame.com>/my.awesomegame.com.pem
    server localhost 127.0.0.1:4001
    timeout client 10m
    timeout server 10m
    timeout connect 5m

listen evennia-secure-websocket
    bind my.awesomegame.com:4002 ssl no-sslv3 no-tlsv10 crt /etc/letsencrypt/live/my.awesomegame.com/my.awesomegame.com.pem
    server localhost 127.0.0.1:4002
    timeout client 10m
    timeout server 10m
    timeout connect 5m
```

## 整合所有内容

返回到 Evennia 游戏目录并编辑 `mygame/server/conf/settings.py`。添加：

```python
WEBSERVER_INTERFACES = ['127.0.0.1']
WEBSOCKET_CLIENT_INTERFACE = '127.0.0.1'
```

以及

```python
WEBSOCKET_CLIENT_URL="wss://my.awesomegame.com:4002/"
```

确保完全重启（停止+启动）Evennia：

```bash
evennia reboot
```

最后启动代理：

```bash
sudo haproxy -f /path/to/the/above/haproxy.cfg
```

确保你可以从浏览器连接到你的游戏，并且你最终看到的是一个 `https://` 页面，并可以使用 WebSocket Web 客户端。

一旦一切正常，你可能希望自动启动代理并在后台运行。使用 `Ctrl-C` 停止代理，并确保取消注释配置文件中的 `# daemon` 行。

如果你的服务器上没有其他代理运行，你可以将你的 haproxy.conf 文件复制到系统范围的设置中：

```bash
sudo cp /path/to/the/above/haproxy.cfg /etc/haproxy/
```

代理现在将在重新加载时启动，你可以使用以下命令控制它：

```bash
sudo service haproxy start|stop|restart|status
```

如果你不想将内容复制到 `/etc/` 中，你也可以通过在服务器重启时使用 `cron` 运行 haproxy 来纯粹从当前位置运行它。再次打开 crontab：

```bash
sudo crontab -e
```

在文件末尾添加新行：

```bash
@reboot haproxy -f /path/to/the/above/haproxy.cfg
```

保存文件，haproxy 应该在你重启服务器时自动启动。接下来只需手动最后一次重启代理——在配置文件中取消注释 `daemon` 后，它将作为后台进程启动。
