# HAProxy Config (Optional)

### Evennia, HTTPS and Secure Websockets can play nicely together, quickly.

This sets up HAProxy 1.5+ in front of Evennia to provide security.

Installing HAProxy is usually as simple as:
```
# Redhat derivatives
yum install haproxy
# dnf instead of yum for very recent Fedora distros.
```
or
```
# Debian derivatives
apt install haproxy
```

Configuration of HAProxy requires a single file given as an argument on the command line:
```
haproxy -f /path/to/config.file
```

In it (example using haproxy 1.5.18 on Centos7):
```
# stuff provided by the default haproxy installs
global
    log /dev/log local0
    chroot /var/lib/haproxy
    maxconn  4000
    user  haproxy
defaults
    mode http
    option forwardfor

# Evennia Specifics
listen evennia-https-website
    bind <public-ip-address>:<public-SSL-port--probably-443> ssl no-sslv3 no-tlsv10 crt
/path/to/your-cert.pem
    server localhost 127.0.0.1:<evennia-web-port-probably-4001>

listen evennia-secure-websocket
    bind <public-ip-address>:<WEBSOCKET_CLIENT_URL 4002> ssl no-sslv3 no-tlsv10 crt /path/to/your-
cert.pem
    server localhost 127.0.0.1:<WEBSOCKET_CLIENT_URL 4002>
    timeout client 10m
    timeout server 10m
```

Then edit mygame/server/conf/settings.py and add:
```
WEBSERVER_INTERFACES = ['127.0.0.1']
WEBSOCKET_CLIENT_INTERFACE = '127.0.0.1'
```
or
```
LOCKDOWN_MODE=True
```
and
```
WEBSOCKET_CLIENT_URL="wss://yourhost.com:4002/"
```
