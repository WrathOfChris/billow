from . import asg
from . import dns
from . import elb
from . import sec
import boto
from .billowRegion import billowRegion


class billowCloud(object):

    """
    a large undulating mass of cloud services
    """

    def __init__(self, regions=['us-east-1']):
        if not isinstance(regions, list):
            regions = list(regions)

        self.regions = list()
        for r in regions:
            self.regions.append(billowRegion(region=r, parent=self))

        self.services = list()

    def list_services(self):
        self.services = list()
        for r in self.regions:
            self.add_services(r.list_services())
        return self.services

    def add_services(self, services):
        for v in services:
            self.services.append(v)

    def get_service(self, services, region=None):
        if not services:
            return list()
        if not isinstance(services, list):
            services = [services]
        out = list()

        for s in services:
            if ':' in s:
                if not region:
                    region = s.split(':')[1]
                service = s.split(':')[0]

            for r in self.regions:
                if region and r.region != region:
                    continue
                svc = r.get_service(s)
                out.extend(svc)

        return out
