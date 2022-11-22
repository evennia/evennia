# Configuring an Apache Proxy

Evennia has its own webserver. This should usually not be replaced. But another reason for wanting to use an external webserver like Apache would be to act as a *proxy* in front of the Evennia webserver. Getting this working with TLS (encryption) requires some extra work covered at the end of this page. 

```{warning} Possibly outdated
The Apache instructions below might be outdated. If something is not working right, or you use Evennia with a different server, please let us know. 
```

## Running Apache as a proxy in front of Evennia 

Below are steps to run Evennia using a front-end proxy (Apache HTTP), `mod_proxy_http`,
`mod_proxy_wstunnel`, and `mod_ssl`. `mod_proxy_http` and `mod_proxy_wstunnel` will simply be
referred to as `mod_proxy` below. 

### Install `mod_ssl`

- *Fedora/RHEL* - Apache HTTP Server and `mod_ssl` are available in the standard package repositories for Fedora and RHEL:
    ```
    $ dnf install httpd mod_ssl
    or
    $ yum install httpd mod_ssl
    
    ```
- *Ubuntu/Debian* - Apache HTTP Server and `mod_sslj`kl are installed together in the `apache2` package and available in the standard package repositories for Ubuntu and Debian. `mod_ssl` needs to be enabled after installation:
    ```
    $ apt-get update
    $ apt-get install apache2 
    $ a2enmod ssl

    ```

### TLS proxy+websocket configuration

Below is a sample configuration for Evennia with a TLS-enabled http and websocket proxy.

#### Apache HTTP Server Configuration

```
<VirtualHost *:80>
  # Always redirect to https/443
  ServerName mud.example.com
  Redirect / https://mud.example.com
</VirtualHost>

<VirtualHost *:443>
  ServerName mud.example.com
  
  SSLEngine On
  
  # Location of certificate and key
  SSLCertificateFile /etc/pki/tls/certs/mud.example.com.crt
  SSLCertificateKeyFile /etc/pki/tls/private/mud.example.com.key
  
  # Use a tool https://www.ssllabs.com/ssltest/ to scan your set after setting up.
  SSLProtocol TLSv1.2
  SSLCipherSuite HIGH:!eNULL:!NULL:!aNULL
  
  # Proxy all websocket traffic to port 4002 in Evennia
  ProxyPass /ws ws://127.0.0.1:4002/
  ProxyPassReverse /ws ws://127.0.0.1:4002/
  
  # Proxy all HTTP traffic to port 4001 in Evennia
  ProxyPass / http://127.0.0.1:4001/
  ProxyPassReverse / http://127.0.0.1:4001/
  
  # Configure separate logging for this Evennia proxy
  ErrorLog logs/evennia_error.log
  CustomLog logs/evennia_access.log combined
</VirtualHost>
```

#### Evennia secure websocket configuration

There is a slight trick in setting up Evennia so websocket traffic is handled correctly by the
proxy. You must set the `WEBSOCKET_CLIENT_URL` setting in your `mymud/server/conf/settings.py` file:

```
WEBSOCKET_CLIENT_URL = "wss://external.example.com/ws"
```

The setting above is what the client's browser will actually use. Note the use of `wss://` is because our client will be communicating over an encrypted connection ("wss" indicates websocket over SSL/TLS). Also, especially note the additional path `/ws` at the end of the URL. This is how
Apache HTTP Server identifies that a particular request should be proxied to Evennia's websocket
port but this should be applicable also to other types of proxies (like nginx). 


## Run Apache instead of the Evennia webserver

```{warning} This is not supported, nor recommended.
This is covered because it has been asked about. The webclient would not work. It would also run out-of-process, leading to race conditions. This is not directly supported, so if you try this you are on your own. 
```

### Install `mod_wsgi`

- *Fedora/RHEL* - Apache HTTP Server and `mod_wsgi` are available in the standard package
repositories for Fedora and RHEL:
    ```
    $ dnf install httpd mod_wsgi
    or
    $ yum install httpd mod_wsgi
    ```
- *Ubuntu/Debian* -  Apache HTTP Server and `mod_wsgi` are available in the standard package
repositories for Ubuntu and Debian:
   ```
   $ apt-get update
   $ apt-get install apache2 libapache2-mod-wsgi
   ```

### Copy and modify the VHOST

After `mod_wsgi` is installed, copy the `evennia/web/utils/evennia_wsgi_apache.conf` file to your
apache2 vhosts/sites folder. On Debian/Ubuntu, this is `/etc/apache2/sites-enabled/`. Make your
modifications **after** copying the file there.

Read the comments and change the paths to point to the appropriate locations within your setup.

### Restart/Reload Apache

You'll then want to reload or restart apache2 after changing the configurations.

- *Fedora/RHEL/Ubuntu*
    ```
    $ systemctl restart httpd
    ```
- *Ubuntu/Debian*
    ```
    $ systemctl restart apache2
    ```

With any luck, you'll be able to point your browser at your domain or subdomain that you set up in
your vhost and see the nifty default Evennia webpage. If not, read the hopefully informative error
message and work from there. Questions may be directed to our [Evennia Community
site](https://evennia.com).

### A note on code reloading

If your `mod_wsgi` is set up to run on daemon mode (as will be the case by default on Debian and
Ubuntu), you may tell `mod_wsgi` to reload by using the `touch` command on
`evennia/game/web/utils/apache_wsgi.conf`. When `mod_wsgi` sees that the file modification time has
changed, it will force a code reload. Any modifications to the code will not be propagated to the
live instance of your site until reloaded.

If you are not running in daemon mode or want to force the issue, simply restart or reload apache2
to apply your changes.

### Further notes and hints:

If you get strange (and usually uninformative) `Permission denied` errors from Apache, make sure
that your `evennia` directory is located in a place the webserver may actually access. For example,
some Linux distributions may default to very restrictive access permissions on a user's `/home`
directory. 

One user commented that they had to add the following to their Apache config to get things to work.
Not confirmed, but worth trying if there are trouble.

    <Directory "/home/<yourname>/evennia/game/web">
                    Options +ExecCGI
                    Allow from all
    </Directory>