#!/bin/bash

# Requires pyasn and geoip2
#pip install -U geoip2 pyasn

echo "Downloading ASN CIDR DB... (1/3)"
pyasn_util_download.py --latest
pyasn_util_convert.py --single rib.* pyasn.dat

echo "Downloading MaxMind GeoIP City database...(2/3)"
wget http://geolite.maxmind.com/download/geoip/database/GeoLite2-City.tar.gz
tar -zxf ./GeoLite2-City.tar.gz --no-anchored GeoLite2-City.mmdb --transform='s/.*\///'

echo "Downloading MaxMind GeoIP ASN database...(3/3)"
wget http://geolite.maxmind.com/download/geoip/database/GeoLite2-ASN.tar.gz
tar -zxf ./GeoLite2-ASN.tar.gz --no-anchored GeoLite2-ASN.mmdb --transform='s/.*\///'

echo "Cleaning up downloaded files..."
rm GeoLite2-*.tar.gz
rm rib.*

echo "Done!"