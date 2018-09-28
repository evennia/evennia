from evennia.contrib.security.geoip import GeoIP
from evennia.utils.test_resources import EvenniaTest

class TestGeoIP(EvenniaTest):
    
    ip = '162.251.81.235'
    
    def test_geoip(self):
        "Make sure GeoIP module is looking up IPs as expected."
        g = GeoIP()
        
        country = g.country(self.ip)
        self.assertTrue(country, 'Country lookup for %s returned %s.' % (self.ip, country))
        
        city = g.city(self.ip)
        self.assertTrue(city, 'City lookup for %s returned %s.' % (self.ip, city))
        
        isp = g.isp(self.ip)
        self.assertTrue(isp, 'ISP lookup for %s returned %s.' % (self.ip, isp))