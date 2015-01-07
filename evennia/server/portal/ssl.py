"""
This is a simple context factory for auto-creating
SSL keys and certificates.
"""

import os
import sys
from twisted.internet import ssl as twisted_ssl
try:
    import OpenSSL
except ImportError:
    print "  SSL_ENABLED requires PyOpenSSL."
    sys.exit(5)

from evennia.server.portal.telnet import TelnetProtocol


class SSLProtocol(TelnetProtocol):
    """
    Communication is the same as telnet, except data transfer
    is done with encryption.
    """
    pass


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

        print "  Creating SSL key and certificate ... ",

        try:
            # create the RSA key and store it.
            KEY_LENGTH = 1024
            rsaKey = Key(RSA.generate(KEY_LENGTH))
            keyString = rsaKey.toString(type="OPENSSH")
            file(keyfile, 'w+b').write(keyString)
        except Exception, e:
            print "rsaKey error: %(e)s\n WARNING: Evennia could not auto-generate SSL private key." % {'e': e}
            print "If this error persists, create game/%(keyfile)s yourself using third-party tools." % {'keyfile': keyfile}
            sys.exit(5)

        # try to create the certificate
        CERT_EXPIRE = 365 * 20  # twenty years validity
        # default:
        #openssl req -new -x509 -key ssl.key -out ssl.cert -days 7300
        exestring = "openssl req -new -x509 -key %s -out %s -days %s" % (keyfile, certfile, CERT_EXPIRE)
        #print "exestring:", exestring
        try:
            #, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            subprocess.call(exestring)
        except OSError, e:
            string = "\n".join([
                 "  %s\n" % e,
                 "  Evennia's SSL context factory could not automatically",
                 "  create an SSL certificate game/%(cert)s." % {'cert': certfile},
                 "  A private key 'ssl.key' was already created. Please",
                 "  create %(cert)s manually using the commands valid" % {'cert': certfile},
                 "  for your operating system.",
                 "  Example (linux, using the openssl program): ",
                 "    %s" % exestring])
            print string
            sys.exit(5)
        print "done."


def getSSLContext():
    """
    Returns an SSL context (key and certificate). This function
    verifies that key/cert exists before obtaining the context, and if
    not, creates them.
    """
    keyfile, certfile = "ssl.key", "ssl.cert"
    verify_SSL_key_and_cert(keyfile, certfile)
    return twisted_ssl.DefaultOpenSSLContextFactory(keyfile, certfile)
