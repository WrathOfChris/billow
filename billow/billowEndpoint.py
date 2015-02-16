from . import dns
import boto
import datetime


class billowEndpoint(object):

    """
    DNS endpoint(s)

    Builds a reverse-index of the zones provided to query by value

    This is arbitrarily gross, as there is no query API for route53 beyond
    specific records by record name.
    """

    def __init__(self, zones, region):
        if not isinstance(zones, list):
            zones = [zones]

        self.zones = zones
        self.region = region
        self.roles = dict()
        self.reverse = dict()
        self.rawzones = None

        self.dns = dns.dns(region)

        for z in self.zones[:]:
            if z.endswith('.'):
                z = z[:-1]

    def __load(self):
        if not self.rawzones:
            self.rawzones = dict()
            for z in self.zones:
                role = None
                if z in self.roles:
                    role = self.roles[z]
                self.rawzones[z] = self.dns.get_records(z, role=role)

            for k, v in self.rawzones.iteritems():
                for zr in v:
                    if zr.type != 'CNAME' and zr.type != 'A':
                        continue

                    name = zr.name
                    if name.endswith('.'):
                        name = name[:-1]

                    if zr.type == 'CNAME':
                        for r in zr.resource_records:
                            dest = r
                            if dest.endswith('.'):
                                dest = dest[:-1]
                            if dest in self.reverse:
                                if name not in self.reverse[dest]:
                                    self.reverse[dest].append(name)
                            else:
                                self.reverse[dest] = [name]

                    if zr.type == 'A' and zr.alias_dns_name:
                        dest = zr.alias_dns_name
                        if dest.endswith('.'):
                            dest = dest[:-1]
                        if dest in self.reverse:
                            if name not in self.reverse[dest]:
                                self.reverse[dest].append(name)
                        else:
                            self.reverse[dest] = [name]

    def set_role(self, zone, role):
        if zone not in self.zones:
            self.zones.append(zone)
        self.roles[zone] = role
        self.rawzones = None
        self.reverse = dict()

    def add_zone(self, zone):
        if zone not in self.zones:
            self.zones.append(zone)
        if zone in self.roles:
            del self.roles[zone]
        self.rawzones = None
        self.reverse = dict()

    def find_destination(self, name):
        self.__load()
        if name.endswith('.'):
            name = name[:-1]
        if name in self.reverse:
            return self.reverse[name]
        return list()
