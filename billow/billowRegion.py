from . import asg
from . import dns
from . import elb
from . import sec
import boto
from .billowService import billowService
from .billowGroup import billowGroup

class billowRegion():
    """
    a large undulating mass of cloud services
    """

    def __init__(self, region='us-east-1'):
        self.region = region

        # Backends
        self.asg = asg.asg(region)
        self.dns = dns.dns(region)
        self.elb = elb.elb(region)
        self.sec = sec.sec(region)

        self.services = dict()

        self.tagservice = 'service'
        self.tagenviron = 'env'
        self.servicetags = [ self.tagenviron, self.tagservice ]

    def list_services(self):
        self.services = dict()
        tags = self.asg.list_tags(tag=self.servicetags)

        # service
        for t in tags:
            if t.key == self.tagservice:
                self.add_service(t.value, t.resource_id)

        # environ
        for t in tags:
            if t.key == self.tagenviron:
                self.update_group_environ(t.resource_id, t.value)

        return self.services.values()

    def add_service(self, service, group=None):
        """
        u'servicename': {
            'groups': [u'servicename-env'],
            'region': 'us-east-1',
            'service': u'servicename',
            'environ': u'environment'
        }
        """
        if service not in self.services:
            self.services[service] = billowService(
                    service,
                    list(),
                    self.region)
        if group:
            if group not in self.services[service].groups:
                self.services[service].groups.append(
                        billowGroup(group, region=self.region))

    def update_group_environ(self, group, environ):
        for k, v in self.services.iteritems():
            if v.environ:
                continue
            for g in v.groups:
                if g == group:
                    if v.environ and v.environ != environ:
                        sys.stderr.write("billowRegion: environ overwrite \
                                %s -> %s" % v.environ, environ)
                    v.environ = environ
                    return
