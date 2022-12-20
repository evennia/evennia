"""
This allows for running the telnet communication over an encrypted SSL tunnel. To use it, requires a
client supporting Telnet SSL.

The protocol will try to automatically create the private key and certificate on the server side
when starting and will warn if this was not possible. These will appear as files ssl.key and
ssl.cert in mygame/server/.

"""
import os

try:
    from OpenSSL import crypto
    from twisted.internet import ssl as twisted_ssl
except ImportError as error:
    errstr = """
    {err}
    Telnet-SSL requires the PyOpenSSL library and dependencies:

        pip install pyopenssl pycrypto enum pyasn1 service_identity

    Stop and start Evennia again. If no certificate can be generated, you'll
    get a suggestion for a (linux) command to generate this locally.

    """
    raise ImportError(errstr.format(err=error))

from django.conf import settings

from evennia.server.portal.telnet import TelnetProtocol

_GAME_DIR = settings.GAME_DIR

_PRIVATE_KEY_LENGTH = 2048
_PRIVATE_KEY_FILE = os.path.join(_GAME_DIR, "server", "ssl.key")
_PUBLIC_KEY_FILE = os.path.join(_GAME_DIR, "server", "ssl-public.key")
_CERTIFICATE_FILE = os.path.join(_GAME_DIR, "server", "ssl.cert")
_CERTIFICATE_EXPIRE = 365 * 24 * 60 * 60 * 20  # 20 years
_CERTIFICATE_ISSUER = {
    "C": "EV",
    "ST": "Evennia",
    "L": "Evennia",
    "O": "Evennia Security",
    "OU": "Evennia Department",
    "CN": "evennia",
}

# messages

NO_AUTOGEN = f"""
Evennia could not auto-generate the SSL private- and public keys ({{err}}).
If this error persists, create them manually (using the tools for your OS). The files
should be placed and named like this:
    {_PRIVATE_KEY_FILE}
    {_PUBLIC_KEY_FILE}
"""

NO_AUTOCERT = """
Evennia's could not auto-generate the SSL certificate ({{err}}).
The private key already exists here:
    {_PRIVATE_KEY_FILE}
If this error persists, create the certificate manually (using the private key and
the tools for your OS). The file should be placed and named like this:
    {_CERTIFICATE_FILE}
"""


class SSLProtocol(TelnetProtocol):
    """
    Communication is the same as telnet, except data transfer
    is done with encryption set up by the portal at start time.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.protocol_key = "telnet/ssl"


def verify_or_create_SSL_key_and_cert(keyfile, certfile):
    """
    Verify or create new key/certificate files.

    Args:
        keyfile (str): Path to ssl.key file.
        certfile (str): Parth to ssl.cert file.

    Notes:
        If files don't already exist, they are created.

    """

    if not (os.path.exists(keyfile) and os.path.exists(certfile)):
        # key/cert does not exist. Create.
        try:
            # generate the keypair
            keypair = crypto.PKey()
            keypair.generate_key(crypto.TYPE_RSA, _PRIVATE_KEY_LENGTH)

            with open(_PRIVATE_KEY_FILE, "wt") as pfile:
                pfile.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, keypair).decode("utf-8"))
                print("Created SSL private key in '{}'.".format(_PRIVATE_KEY_FILE))

            with open(_PUBLIC_KEY_FILE, "wt") as pfile:
                pfile.write(crypto.dump_publickey(crypto.FILETYPE_PEM, keypair).decode("utf-8"))
                print("Created SSL public key in '{}'.".format(_PUBLIC_KEY_FILE))

        except Exception as err:
            print(NO_AUTOGEN.format(err=err))
            return False

        else:

            try:
                # create certificate
                cert = crypto.X509()
                subj = cert.get_subject()
                for key, value in _CERTIFICATE_ISSUER.items():
                    setattr(subj, key, value)
                cert.set_issuer(subj)

                cert.set_serial_number(1000)
                cert.gmtime_adj_notBefore(0)
                cert.gmtime_adj_notAfter(_CERTIFICATE_EXPIRE)
                cert.set_pubkey(keypair)
                cert.sign(keypair, "sha1")

                with open(_CERTIFICATE_FILE, "wt") as cfile:
                    cfile.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode("utf-8"))
                    print("Created SSL certificate in '{}'.".format(_CERTIFICATE_FILE))

            except Exception as err:
                print(NO_AUTOCERT.format(err=err))
                return False

    return True


def getSSLContext():
    """
    This is called by the portal when creating the SSL context
    server-side.

    Returns:
        ssl_context (tuple): A key and certificate that is either
            existing previously or created on the fly.

    """

    if verify_or_create_SSL_key_and_cert(_PRIVATE_KEY_FILE, _CERTIFICATE_FILE):
        return twisted_ssl.DefaultOpenSSLContextFactory(_PRIVATE_KEY_FILE, _CERTIFICATE_FILE)
    else:
        return None
