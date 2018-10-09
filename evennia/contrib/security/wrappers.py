from django.conf import settings
from django.contrib import messages
from evennia.utils import class_from_module, logger
from netaddr import IPAddress, IPNetwork

GEOIP_CLASS = class_from_module(getattr(settings, 'GEOIP_CLASS', 'django.contrib.gis.geoip2.GeoIP2'))
GEOIP_PATH = getattr(settings, 'GEOIP_PATH', settings.GAME_DIR)
try:
    GEO_DB = GEOIP_CLASS(path=GEOIP_PATH)
except:
    GEO_DB = None

class ConnectionWrapper(object):
    """
    Wraps an object representing some sort of network connection and maps its
    properties to a set of well-known artifacts.
    """
    @property
    def account(self):
        """
        Returns the account associated with the connection, if authenticated.
        """
        return self.get_account()
    
    @property
    def asn(self):
        """
        The Autonomous System number of the client IP.
        
        Returns:
            asn (str): AS number cast as string, due to external data 
                inconsistencies.
                
        """
        return str(self._geoip.get('asn', ''))
        
    @property
    def asn_org(self):
        """
        Autonomous System organization name. Often the same as the ISP, although
        it is technically a greater collective a group of ISPs participate in.
        
        Returns:
            org (str): Organization name.
            
        """
        return str(self._geoip.get('autonomous_system_organization', ''))
        
    @property
    def cidr(self):
        """
        CIDR block of an IP.
        
        If experiencing abuse from multiple IPs that are similar in appearance
        (part of the same class A or ASN), this will return the entire subnet
        they're using in CIDR notation.
        
        The advantage to this is that you can more accurately target bans; no
        more assuming every subnet is a /24 or trying to ban a country by
        targeting an entire class A.
        
        Returns:
            cidr (str): CIDR notation of an IP subnet; i.e. 5.123.23.44/30
        
        """
        # If no CIDR was found, return the smallest 
        # possible subnet (ipv4 = */32)
        return self._geoip.get('cidr', str(IPNetwork(self.ip).cidr))
        
    @property
    def client(self):
        """
        Convenience property to return the client or useragent being used for
        a given connection.
        
        """
        return self.get_client()
        
    @property
    def country(self):
        """
        Returns country code for the origin of a given connection.
        
        Returns:
            iso (str): ISO country code ('US', 'KR', 'RU')
        
        """
        return self.iso
        
    @property
    def customer(self):
        """
        Where possible, returns the name of the customer of an ISP.
        
        For example, an AS org might be Leaseweb, but they might be leasing lines
        to NordVPN. NordVPN is the customer.
        
        Requires paid license for MaxMind ISP DB, but will return AS org when
        no more specific value is found.
        
        Returns:
            customer (str): Name of organization.
        
        """
        return self._geoip.get('organization', '')
    
    @property
    def ip(self):
        """
        IP address for the origin of a given connection.
        
        Returns:
            ip (str): IP address.
        
        """
        return self.get_ip()
    
    @property
    def iso(self):
        """
        ISO country code for the origin of a given connection.
        
        Returns:
            iso (str): 2-letter country ISO code.
        
        """
        return self._geoip.get('country_code', '')
    
    @property
    def isp(self):
        """
        Returns the most specific provider information available for the IP
        associated with the origin connection.
        
        Returns:
            isp (str): Either the name of the ISP, a serviced organization or
                the autonomous system organization.
                
        """
        values = (self._geoip.get(x) for x in ('isp', 'organization', 'autonomous_system_organization'))
        return next((x for x in values if x), '')
    
    @property
    def protocol(self):
        """
        Protocol in use by the connection.
        
        Returns:
            protocol (str): Brief descriptor of protocol (ssh, https, etc.)
            
        """
        return self.get_protocol()
    
    @property
    def useragent(self):
        """
        Useragent or client being used by the origin connection, where
        discernable.
        
        Returns:
            useragent (str): Useragent or client string.
        
        """
        return self.get_useragent()
        
    @property
    def who(self):
        """
        Convenience property to return customer name, where available.
        
        """
        return self.customer
    
    def __init__(self, connection_object):
        """
        Constructor for wrapper.
        
        Args:
            connection_object (any): Object representing some sort of connection
                between the client and server.
                
        """
        self.obj = connection_object
        
        template = {}
        template['ip'] = ip = self.get_ip()
        ip_obj = IPAddress(ip)
        
        # Look up as much geodata as available, cache it locally
        if GEO_DB and not ip_obj.is_private() and not ip_obj.is_loopback():
            for artifact in ('country', 'city', 'isp'):
                try: template.update(getattr(GEO_DB, artifact)(ip))
                except: pass
        
        self._geoip = template
        
    def __str__(self):
        return str(self.obj)
        
    def __getattr__(self,attr):
        """
        Forward any unknown function calls to the connection object.
        """
        return getattr(self.obj, attr)
        
    def get_account(self):
        raise Exception("Method not implemented!")
        
    def get_client(self):
        return self.get_useragent()
        
    def get_ip(self):
        raise Exception("Method not implemented!")
        
    def get_protocol(self):
        raise Exception("Method not implemented!")
        
    def get_username(self):
        return self.get_account.name
            
    def get_useragent(self):
        raise Exception("Method not implemented!")
        
    def msg(self):
        raise Exception("Method not implemented!")

class RequestWrapper(ConnectionWrapper):
    """
    Wrapper for Django HttpRequest objects.
    """
    def get_account(self):
        # Get user object from request
        if self.obj.user.is_authenticated():
            return self.obj.user
        else:
            return None
    
    def get_ip(self):
        # Get IP from HttpRequest object
        xff = self.obj.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            # Get the first non-RFC1918 address
            ip = next((ip for ip in [IPAddress(x) for x in xff.split(',')] if (not ip.is_private() and not ip.is_loopback())), None)
            if ip: return str(ip)
        
        return self.obj.META.get('REMOTE_ADDR')
    
    def get_protocol(self):
        # Get protocol from request (requires Django 1.10+)
        return self.obj.scheme
    
    def get_useragent(self):
        # Get useragent string from request
        return self.obj.META.get('HTTP_USER_AGENT', '')
        
    def msg(self, msg):
        # Send message to browser using Messages framework
        messages.info(self.obj, msg)
            
class SessionWrapper(ConnectionWrapper):
    """
    Wrapper for Evennia Session objects.
    """
    def get_account(self):
        # Get user/account id from session
        uid = self.obj.uid
        
        # Get account object
        if uid:
            return AccountDB.objects.get_account_from_uid(uid)
        else:
            return None
    
    def get_ip(self):
        # Get IP from Session object
        address = self.obj.address
        if isinstance(address, tuple):
            address = address[0]
            
        return address
    
    def get_protocol(self):
        # Get protocol from session
        return self.obj.protocol_key
    
    def get_useragent(self):
        # Get client string from session
        return self.obj.protocol_flags.get('CLIENT_NAME', '')
        
    def msg(self, msg):
        # Send message to browser using terminal
        self.obj.msg(msg)