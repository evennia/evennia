from django.conf import settings
from django.contrib.gis.geoip2 import GeoIP2 as DjangoGeoIP2, GeoIP2Exception
from django.core.validators import validate_ipv46_address
from evennia.utils import logger

from pathlib import Path

import geoip2.database
import os
import pyasn
import socket

# Creating the settings dictionary with any settings, if needed.
GEOIP_SETTINGS = {
    'GEOIP_PATH': getattr(settings, 'GEOIP_PATH', os.getcwd()),
    'GEOIP_CITY': getattr(settings, 'GEOIP_CITY', 'GeoLite2-City.mmdb'),
    'GEOIP_COUNTRY': getattr(settings, 'GEOIP_COUNTRY', 'GeoLite2-Country.mmdb'),
    'GEOIP_ASN': getattr(settings, 'GEOIP_ASN', 'GeoLite2-ASN.mmdb'),
    'GEOIP_CIDR': getattr(settings, 'GEOIP_CIDR', 'pyasn.dat'),
}

def ISP(response):
    " Template for ISP data returned from the DB "
    return {
        'autonomous_system_number': response.autonomous_system_number,
        'autonomous_system_organization': response.autonomous_system_organization,
        'cidr': response.network,
        'isp': getattr(response, 'isp', response.autonomous_system_organization),
        'organization': getattr(response, 'organization', response.autonomous_system_organization),
    }

class GeoIP(DjangoGeoIP2):
    """
    Improved version of Django GeoIP wrapper.
    
    Enables lookup of ISP/ASN data, with CIDR block, via additional databases.
    
    All source databases are updated monthly, but yours will eventually become
    stale if you don't update them yourself!
    
    To install:
        
        Run update_dbs.sh in a directory you wish to store the database files
        we need to download; location doesn't matter, just remember where you
        ran the script from.
        
        In settings.py, set:
            
            GEOIP_PATH = <path to that location>
            
    To update:
    
        Run update_dbs.sh in the same directory you did the first time. No new
        configuration is required, though changes may not take effect until
        you reload the server.
        
    To use:
    
        # Instantiate
        g = GeoIP()
        
        # Get attributes of the IP (returns dict)
        g.country(ip)
        g.city(ip)
        g.isp(ip)
        
    """
    def __init__(self, path=None, cache=0, country=None, city=None, asn=None, cidr=None):
        
        # Getting the GeoIP data path.
        path = path or GEOIP_SETTINGS['GEOIP_PATH']
        if not path:
            raise GeoIP2Exception('GeoIP path must be provided via parameter or the GEOIP_PATH setting.')
        if not isinstance(path, str):
            raise TypeError('Invalid path type: %s' % type(path).__name__)(path)
        
        # Do all the parent init stuff
        super(GeoIP, self).__init__(path, cache, country, city)
        
        path = Path(path)
        
        # Load the ASN database
        asn_db = path / (asn or GEOIP_SETTINGS['GEOIP_ASN'])
        if asn_db.is_file():
            self._asn = geoip2.database.Reader(str(asn_db), mode=cache)
            self._asn_file = asn_db
        
        # MaxMind ASN DB currently does not return CIDR blocks, while their
        # CSV offerings do. To compensate we'll compile our own table and use
        # pyasn to query it.
        #
        # Technically we could use pyasn in place of the MaxMind ASN DB but
        # doing things this way, one has the option of using the free ASN DB or
        # their commercial ISP DB-- they are interchangeable to the API.
        
        # Load the CIDR database
        cidr_db = path / (cidr or GEOIP_SETTINGS['GEOIP_CIDR'])
        if cidr_db.is_file():
            self._cidr = pyasn.pyasn(str(cidr_db))
            self._cidr_file = cidr_db
        
    def asn(self, query):
        return self.isp(query)
        
    def cidr(self, query):
        """
        Return a dictionary with a single key:value pair indicating the IP's
        CIDR block.
        """
        try:
            validate_ipv46_address(query)
        except ValidationError:
            query = socket.gethostbyname(query)
        
        try:
            response = {'cidr': self._cidr.lookup(str(query))[1]}
        except AttributeError:
            logger.log_err('GeoIP: CIDR data requested, but no database was configured.')
            return {}
        
        return response
        
    def country(self, query):
        try:
            return super(GeoIP, self).country(query)
        except GeoIP2Exception as e:
            logger.log_err('GeoIP: %s' % e)
            return {}
            
    def city(self, query):
        try:
            return super(GeoIP, self).city(query)
        except GeoIP2Exception as e:
            logger.log_err('GeoIP: %s' % e)
            return {}
            
    def isp(self, query):
        """
        Return a dictionary of ISP information for the given IP address or
        Fully Qualified Domain Name (FQDN). Some information in the dictionary
        may be undefined (None).
        """
        try:
            validate_ipv46_address(query)
        except ValidationError:
            query = socket.gethostbyname(query)
        
        try:
            response = self._asn.asn(query)
        except AttributeError:
            logger.log_err('GeoIP: ASN/ISP data requested, but no database was configured.')
            return {}
        
        # Re-add CIDR data to MaxMind's output
        response.network = self.cidr(query).get('cidr', '')
        
        return ISP(response)