# 为 Evennia 配置 NGINX 以支持 SSL

[Nginx](https://nginx.org/en/) 是一个代理服务器；你可以将它放在 Evennia 和外部世界之间，通过加密连接提供你的游戏。另一种选择是 [HAProxy](./Config-HAProxy.md)。

> 这不是一个完整的设置指南！它假设你知道如何获取自己的 `Letsencrypt` 证书，已经安装了 nginx，并且熟悉 Nginx 配置文件。**如果你还没有使用 nginx，** 你可能更适合使用 [HAProxy 指南](./Config-HAProxy.md)。

## 网站和 WebSocket 的 SSL

网站和 WebSocket 都应该通过你正常的 HTTPS 端口访问，因此它们应该一起定义。

对于 nginx，以下是一个使用 Evennia 默认端口的示例配置：

```nginx
server {
    server_name example.com;

    listen [::]:443 ssl;
    listen 443 ssl;
    ssl_certificate  /path/to/your/cert/file;
    ssl_certificate_key /path/to/your/cert/key;

    location /ws {
        # WebSocket 连接
        proxy_pass http://localhost:4002;
        proxy_http_version 1.1;
        # 允许握手升级连接
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        # 转发连接 IP
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
    }

    location / {
        # 主网站
        proxy_pass http://localhost:4001;
        proxy_http_version 1.1;
        # 转发连接 IP
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

这将通过 `/ws` 位置代理 WebSocket 连接，并将根位置代理到网站。

对于 Evennia，以下是与上述 nginx 配置配套的示例设置配置，放在你的生产服务器的 `server/conf/secret_settings.py` 中。

> `secret_settings.py` 文件不包含在 `git` 提交中，用于存放秘密内容。将仅限生产环境的设置放在此文件中，可以让你继续使用默认的访问点进行本地开发，简化你的工作。

```python
SERVER_HOSTNAME = "example.com"
# 设置 WebSocket 的完整 URI，包括方案
WEBSOCKET_CLIENT_URL = "wss://example.com/ws"
# 关闭所有外部连接
LOCKDOWN_MODE = True
```

这确保了 Evennia 使用正确的 URI 进行 WebSocket 连接。设置 `LOCKDOWN_MODE` 为开启状态还会防止任何直接连接到 Evennia 端口的外部连接，将其限制为通过 nginx 代理的连接。

## Telnet SSL

> 这将通过 nginx 代理所有的 Telnet 访问！如果你希望玩家直接连接到 Evennia 的 Telnet 端口而不是通过 nginx，请关闭 `LOCKDOWN_MODE` 并使用其他 SSL 实现，例如激活 Evennia 的内部 Telnet SSL 端口（请参阅 [默认设置文件](./Settings-Default.md) 中的 `settings.SSL_ENABLED` 和 `settings.SSL_PORTS`）。

如果你只为网站使用过 nginx，Telnet 会稍微复杂一些。你需要在主配置文件中设置流参数，例如 `/etc/nginx/nginx.conf`，而默认安装通常不会包含这些参数。

我们选择为 `stream` 并行 `http` 结构，添加 conf 文件到 `streams-available`，并将它们符号链接到 `streams-enabled`，与其他站点相同。

```nginx
stream {
    include /etc/nginx/conf.streams.d/*.conf;
    include /etc/nginx/streams-enabled/*;
}
```

然后当然你需要在与你的其他 nginx 配置相同的位置创建所需的文件夹：

```bash
$ sudo mkdir conf.streams.d streams-available streams-enabled
```

Telnet 连接的示例配置文件——使用任意外部端口 `4040`——如下：

```nginx
server {
    listen [::]:4040 ssl;
    listen 4040 ssl;

    ssl_certificate  /path/to/your/cert/file;
    ssl_certificate_key  /path/to/your/cert/key;

    # 连接到 Evennia 的内部非 SSL Telnet 端口
    proxy_pass localhost:4000;
    # 转发连接 IP - 需要 --with-stream-realip-module
    set_real_ip_from $realip_remote_addr:$realip_remote_port
}
```

玩家现在可以通过 telnet+SSL 连接到你的服务器 `example.com:4040`，但*不能*连接到内部连接 `4000`。

> ***重要：使用此配置，默认首页将错误。*** 你需要更改 `index.html` 模板并更新 telnet 部分（而不是 telnet ssl 部分！）以显示正确的信息。

## 不要忘记！

`certbot` 将自动为你续订证书，但 nginx 不会在没有重新加载的情况下看到它们。请确保设置每月的 cron 任务以重新加载你的 nginx 服务，以避免因证书过期而导致的服务中断。
