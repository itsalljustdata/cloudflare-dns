from re import T
import this
from functions import *
from version import getVersion
import CloudFlare
from dataclasses import dataclass
import sys
import re

@dataclass
class dnsEntries():
    entries: list
    def get_dns_by_type(self, typeToMatch):
        # ic (typeToMatch)
        if not typeToMatch:
            return self
        return dnsEntries(self._get_dns_by_type(typeToMatch))

    def _get_dns_by_type(self, typeToMatch):
        if isinstance(typeToMatch,list):
            allMatches = []
            typeToMatch = sorted(typeToMatch)
            for t in typeToMatch:
                matches = self._get_dns_by_type(t)
                allMatches.extend (matches)
            return allMatches
        else:
            return [d for d in self.entries if typeToMatch == d.typ]

    def append (self, entries):
        if isinstance(entries,list):
            self.entries.extend(entries)
        elif isinstance(entries,dnsEntries):
            self.entries.extend(entries.entries)
        else:
            raise Exception ('Invalid parameter type')
@dataclass
class Zone ():
    id : str
    name: str
    dns: dnsEntries
    def get_dns_by_type(self, typeToMatch):
        return self.dns.get_dns_by_type(typeToMatch)

@dataclass
class Zones ():
    z : list
    def get_dns_by_type(self, typeToMatch):
        matches = dnsEntries([])
        for this_z in self.z:
            matches.append(this_z.dns.get_dns_by_type(typeToMatch))

        return matches

@dataclass
class DNS():
    id : str
    name : str
    ttl : int
    typ : str
    priority : int
    value : str
    zoneId : str



def main(theConfig):
    cf = connect(theConfig)
    deleteFilteredZonesByType(cf,['A','AAAA','CNAME'],'iceman')

def getZones(cf):
    zones = cf.zones.get(params={'per_page':100})
    allZones = []
    for z in zones:
        # ic (zone)
        zone_name = z['name']
        zone_id = z['id']
        zone_type = z['type']
        try:
            dns_records = cf.zones.dns_records.get(zone_id)
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            sys.stderr.write('/zones/dns_records %d %s - api call failed\n' % (e, e))
            continue

        prog = re.compile('\.*'+zone_name+'$')
        dns_records = sorted(dns_records, key=lambda v: (v['type'], prog.sub('', v['name']) + '_' + v['type']))
        recs = []
        for dns_record in dns_records:
                r_name = dns_record['name']
                r_type = dns_record['type']
                if 'content' in dns_record:
                    r_value = dns_record['content']
                else:
                    # should not happen
                    r_value = None
                if 'priority' in dns_record:
                    r_priority = int(dns_record['priority'])
                else:
                    r_priority = None
                r_ttl = int(dns_record['ttl'])
                if zone_type == 'secondary':
                    r_id = 'secondary'
                else:
                    r_id = dns_record['id']
                # print('\t%s %60s %6d %-5s %4s %s' % )
                recs.append (DNS(r_id, r_name, r_ttl, r_type, r_priority, r_value, zone_id))
        # settings_ipv6 = cf.zones.settings.ipv6.get(zone_id)
        # ipv6_on = settings_ipv6['value']
        allZones.append (Zone (zone_id, zone_name,dnsEntries(recs)))
    return Zones(allZones)

def getFilteredZonesByType(cf, dnsType, filterString = None):
    filtered = getZones(cf)
    if dnsType:
        filtered = filtered.get_dns_by_type(dnsType)
    if filterString:
        filtered = dnsEntries([d for d in filtered.entries if filterString in d.name or filterString in d.value])
    # ic (filtered)
    return filtered

def deleteFilteredZonesByType(cf, dnsType, filterString = None):
    toDelete = getFilteredZonesByType(cf, dnsType, filterString).entries
    if not toDelete:
        print ("Nothing to do")
        return
    for d in toDelete:
        try:
            dns_record = cf.zones.dns_records.delete(d.zoneId, d.id)
            ic(f'DELETED {d.name}')
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            exit('/zones.dns_records.delete %s - %d %s - api call failed' % (d.name, e, e))
    # for z in allZones:
    #     ic (z.get_dns_by_type(['A','AAAA','CNAME']))
    #     ic (z.get_dns_by_type(['TXT','MX']))


def connect (theConfig):
    return CloudFlare.CloudFlare(token=theConfig.get(['CF','TOKEN']),email=theConfig.get(['CF','EMAIL']))

if __name__ == '__main__':
    configFile = Path('__file__').parent.parent.joinpath('config.yaml')
    if not configFile.is_file():
        configSample = configFile.with_stem(f"{configFile.stem}.sample")
        configFile.write_bytes(configSample.read_bytes())
        raise Exception (f'default {str(configFile)} created, please update values')

    CONFIG = getConfig(configFile)
    ic(getVersion())
    main(CONFIG)
