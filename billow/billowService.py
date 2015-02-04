from . import asg
from . import dns
from . import elb
from . import sec
import boto
import datetime
import pprint
from .billowGroup import billowGroup


class billowService(object):

    """
    a large undulating mass of cloud services
    """

    def __init__(self, service, groups=[], region='us-east-1', environ=None,
            parent=None):
        self.service = service
        self.environ = environ
        self.groups = groups
        self.__region = region
        self.parent = parent

        # service-env:region overrides passed in region
        if ':' in service:
            self.__region = service.split(':')[1]
            self.service = service.split(':')[0]

        # Backends
        if self.parent:
            self.asg = self.parent.asg
            self.dns = self.parent.dns
            self.elb = self.parent.elb
            self.sec = self.parent.sec
        else:
            self.asg = asg.asg(self.region)
            self.dns = dns.dns(self.region)
            self.elb = elb.elb(self.region)
            self.sec = sec.sec(self.region)

        self.tagservice = 'service'

    def config(self):
        self.__config = dict()
        self.__config['region'] = self.region
        self.__config['service'] = self.service
        self.__config['environ'] = self.environ
        if self.cluster:
            self.__config['cluster'] = self.cluster
        self.__config['groups'] = list()
        for g in self.groups:
            self.__config['groups'].append(g.config())
        return self.__config

    def __repr__(self):
        return pprint.pformat(self.config())

    def __str__(self):
        """
        service-env:region
        """
        return '%s-%s:%s' % (self.service, self.environ, self.region)

    def __unicode__(self):
        """
        service-env:region
        """
        return '%s-%s:%s' % (self.service, self.environ, self.region)

    def __eq__(self, other):
        """
        Match strings against 4 forms of service name:
        1. service-environ:region
        2. service-environ
        3. service:region
        4. service
        """
        if isinstance(other, str) or isinstance(other, unicode):
            if "%s-%s:%s" % (self.service, self.environ, self.region) == other:
                return True
            elif "%s-%s" % (self.service, self.environ) == other:
                return True
            elif "%s:%s" % (self.service, self.region) == other:
                return True
            else:
                return self.service == other
        return self.service == other.service and \
            self.environ == other.environ and \
            self.region == other.region

    def _load(self):
        print "loading..."
        self._load_groups()

        # preserve update time for future caching decisions
        self.update_time = datetime.datetime.utcnow()

    def _load_groups(self):
        groupnames = list()
        groups = list()
        baseservice = None

        # find all groups with service=(self)
        tags = self.asg.list_tags(tag=self.tagservice, value=self.service)
        for t in tags:
            groupnames.append(t.resource_id)
        asgs = self.asg.get_groups(groupnames)

        # retrieve all autoscale groups, push in data to save round trips
        for a in asgs:
            g = billowGroup(a.name, region=self.region, parent=self)
            g.push(a)
            groups.append(g)

        # undefined environment - simply select the first seen
        if not self.environ:
            for g in groups:
                self.environ = g.environ
                print "XXX set environ %s" % self.environ
                break

        # prune any groups that do not match the environment
        for g in groups[:]:
            if g.environ != self.environ:
                print "XXX throw away environ %s" % g.environ
                groups.remove(g)

        self.groups = groups

    @property
    def region(self):
        if self.parent:
            return self.parent.region
        else:
            return self.__region

    @property
    def cluster(self):
        """
        return a common cluster name if all groups have the same cluster,
        otherwise None
        """
        cluster = None
        for g in self.groups:
            if not cluster:
                cluster = g.cluster
            if cluster != g.cluster:
                return None
        return cluster

    @property
    def ami(self):
        """
        return a common AMI name if all groups have the same AMI,
        otherwise None
        """
        ami= None
        for g in self.groups:
            if not ami:
                ami = g.ami
            if ami != g.ami:
                return None
        return ami
