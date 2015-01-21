from . import asg
from . import dns
from . import elb
from . import sec
import boto
from .billowRegion import billowRegion

class billowCloud():
    """
    a large undulating mass of cloud services
    """

    def __init__(self, regions=['us-east-1']):
        if not isinstance(regions, list):
            regions = list(regions)

        self.regions = list()
        for r in regions:
            self.regions.append(billowRegion(region=r))

        self.services = dict()

    def list_services(self):
        self.services = dict()
        for r in self.regions:
            r.list_services()
            # use the dict() attribute instead of the returned list()
            self.add_services(r.services)
        return self.services.values()

    def add_services(self, services):
        for k, v in services.iteritems():
            self.services[str(v)] = v
