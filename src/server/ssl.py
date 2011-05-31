"""
This is a simple context factory for auto-creating 
SSL keys and certificates. 
"""

import os, sys
from twisted.internet import ssl as twisted_ssl
try:
    import OpenSSL
except ImportError:
    print "  SSL_ENABLED requires PyOpenSSL."
    sys.exit()

from src.server.telnet import TelnetProtocol

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
        except Exception,e: 
            print "rsaKey error: %s\n WARNING: Evennia could not auto-generate SSL private key." % e
            print "If this error persists, create game/%s yourself using third-party tools." % keyfile
            sys.exit()
            
        # try to create the certificate
        CERT_EXPIRE = 365 * 20 # twenty years validity        
        # default: 
        #openssl req -new -x509 -key ssl.key -out ssl.cert -days 7300
        exestring = "openssl req -new -x509 -key %s -out %s -days %s" % (keyfile, certfile, CERT_EXPIRE)
        #print "exestring:", exestring
        try:
            err = subprocess.call(exestring)#, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except OSError, e:
            print "  %s\n" % e
            print "  Evennia's SSL context factory could not automatically create an SSL certificate game/%s." % certfile
            print "  A private key 'ssl.key' was already created. Please create %s manually using the commands valid " % certfile
            print "  for your operating system." 
            print "  Example (linux, using the openssl program): "
            print "    %s" % exestring
            sys.exit()
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
