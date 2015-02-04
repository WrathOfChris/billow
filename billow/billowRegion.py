from . import asg
from . import dns
from . import elb
from . import sec
import boto
import sys
from .billowService import billowService
from .billowGroup import billowGroup


class billowRegion(object):

    """
    a large undulating mass of cloud services
    """

    def __init__(self, region='us-east-1', parent=None):
        self.region = region
        self.parent = parent
        self.services = list()

        # Backends
        self.asg = asg.asg(self.region)
        self.dns = dns.dns(self.region)
        self.elb = elb.elb(self.region)
        self.sec = sec.sec(self.region)

        self.tagservice = 'service'
        self.tagenviron = 'env'
        self.servicetags = [self.tagenviron, self.tagservice]

    def find_service(self, service, environ=None):
        o = list()
        for s in self.services:
            if s.service == service:
                if environ:
                    if s.environ == environ:
                        o.append(s)
                    continue
                o.append(s)

        return o

    def list_services(self):
        self.services = list()
        servicenames = dict()
        tags = self.asg.list_tags(tag=self.servicetags)

        # service
        for t in tags:
            if t.key == self.tagservice:
                servicenames[t.resource_id] = { 'service': t.value }

        # environ
        for t in tags:
            if t.key == self.tagenviron:
                if t.resource_id not in servicenames:
                    servicenames[t.resource_id] = dict()
                servicenames[t.resource_id]['environ'] = t.value

        for k,v in servicenames.iteritems():
            if 'service' not in v:
                sys.stderr.write("group %s missing service tag\n" % k)
                continue
            if 'environ' not in v:
                sys.stderr.write("group %s missing environ tag\n" % k)
                continue
            self.add_service(v['service'], v['environ'], group=k)

        return self.services

    def add_service(self, service, environ, group=None):
        slist = self.find_service(service, environ=environ)
        if not slist:
            s = billowService(
                service,
                groups=list(),
                region=self.region,
                environ=environ,
                parent=self)
            self.services.append(s)
            slist = [s]

        if len(slist) > 1:
            sys.stderr.write("ignoring multiple services found for %s/%s\n" % (service, environ))

        s = slist[0]
        if group:
            if group not in s.groups:
                s.groups.append(billowGroup(group, region=self.region,
                    parent=s))

        return s

    def canon_service(self, service):
        if ':' in service:
            return service.split(':')[0]

        return service

    def get_service(self, service):
        if not self.services:
            self.list_services()
        service = self.canon_service(service)

        s = self.find_service(service)
        if not s:
            # parse environment if it was present
            if '-' in service:
                sname = service.rsplit('-', 1)[0]
                ename = service.rsplit('-', 1)[1]
                s = self.find_service(sname, environ=ename)
                if not s:
                    return list()

                return s

            return list()

        return s
