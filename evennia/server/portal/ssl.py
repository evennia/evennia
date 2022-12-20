"""
This is a simple context factory for auto-creating
SSL keys and certificates.

"""
import os
import sys

try:
    import OpenSSL
    from twisted.internet import ssl as twisted_ssl
except ImportError as error:
    errstr = """
    {err}
    SSL requires the PyOpenSSL library:
        pip install pyopenssl
    """
    raise ImportError(errstr.format(err=error))

from django.conf import settings

from evennia.utils.utils import class_from_module

_GAME_DIR = settings.GAME_DIR

# messages

NO_AUTOGEN = """

{err}
Evennia could not auto-generate the SSL private key. If this error
persists, create {keyfile} yourself using third-party tools.
"""

NO_AUTOCERT = """

{err}
Evennia's SSL context factory could not automatically, create an SSL
certificate {certfile}.

A private key {keyfile} was already created. Please create {certfile}
manually using the commands valid  for your operating system, for
example (linux, using the openssl program):
    {exestring}
"""

_TELNET_PROTOCOL_CLASS = class_from_module(settings.TELNET_PROTOCOL_CLASS)


class SSLProtocol(_TELNET_PROTOCOL_CLASS):
    """
    Communication is the same as telnet, except data transfer
    is done with encryption.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.protocol_name = "ssl"


def verify_SSL_key_and_cert(keyfile, certfile):
    """
    This function looks for RSA key and certificate in the current
    directory. If files ssl.key and ssl.cert does not exist, they
    are created.

    """

    if not (os.path.exists(keyfile) and os.path.exists(certfile)):
        # key/cert does not exist. Create.
        import subprocess

        from Crypto.PublicKey import RSA
        from twisted.conch.ssh.keys import Key

        print("  Creating SSL key and certificate ... ", end=" ")

        try:
            # create the RSA key and store it.
            KEY_LENGTH = 2048
            rsa_key = Key(RSA.generate(KEY_LENGTH))
            key_string = rsa_key.toString(type="OPENSSH")
            with open(keyfile, "w+b") as fil:
                fil.write(key_string)
        except Exception as err:
            print(NO_AUTOGEN.format(err=err, keyfile=keyfile))
            sys.exit(5)

        # try to create the certificate
        CERT_EXPIRE = 365 * 20  # twenty years validity
        # default:
        # openssl req -new -x509 -key ssl.key -out ssl.cert -days 7300
        exestring = "openssl req -new -x509 -key %s -out %s -days %s" % (
            keyfile,
            certfile,
            CERT_EXPIRE,
        )
        try:
            subprocess.call(exestring)
        except OSError as err:
            raise OSError(
                NO_AUTOCERT.format(err=err, certfile=certfile, keyfile=keyfile, exestring=exestring)
            )
        print("done.")


def getSSLContext():
    """
    This is called by the portal when creating the SSL context
    server-side.

    Returns:
        ssl_context (tuple): A key and certificate that is either
            existing previously or or created on the fly.

    """
    keyfile = os.path.join(_GAME_DIR, "server", "ssl.key")
    certfile = os.path.join(_GAME_DIR, "server", "ssl.cert")

    verify_SSL_key_and_cert(keyfile, certfile)
    return twisted_ssl.DefaultOpenSSLContextFactory(keyfile, certfile)
