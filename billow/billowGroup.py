from . import asg
from . import dns
from . import elb
from . import sec
import boto


class billowGroup():

    """
    a large undulating mass of cloud services
    """

    def __init__(self, group, region='us-east-1'):
        self.group = group
        self.region = region
        self.rawgroup = None

        # Backends
        self.asg = asg.asg(region)
        self.dns = dns.dns(region)
        self.elb = elb.elb(region)
        self.sec = sec.sec(region)

        self.tagservice = 'service'
        self.tagenviron = 'env'
        self.tagcluster = 'cluster'

    def __repr__(self):
        """
        billowGroup(group:region)
        """
        return 'billowGroup(%s:%s)' % (self.group, self.region)

    def __str__(self):
        """
        group
        """
        return '%s' % (self.group)

    def __unicode__(self):
        """
        group
        """
        return u'%s' % (self.group)

    def __eq__(self, other):
        if isinstance(other, str) or isinstance(other, unicode):
            return self.group == other
        return self.group == other.group and \
            self.region == other.region and \
            self.service == other.service and \
            self.environ == other.environ and \
            self.cluster == other.cluster

    def _load(self):
        if not self.rawgroup:
            group = self.asg.get_groups(self.group)
            if len(group) == 1:
                self.rawgroup = group[0]

        for t in self.rawgroup.tags:
            if t.key == self.tagservice:
                self.service = t.value
            elif t.key == self.tagenviron:
                self.environ = t.value
            elif t.key == self.tagcluster:
                self.cluster = t.value

    def refresh(self):
        self.rawgroup = None
        self._load()

    @property
    def service(self):
        self._load()
        return self.service

    @property
    def environ(self):
        self._load()
        return self.environ

    @property
    def cluster(self):
        self._load()
        return self.cluster

    @property
    def name(self):
        self._load()
        return self.rawgroup.name

    @property
    def zones(self):
        self._load()
        return self.rawgroup.availability_zones

    @property
    def cur_size(self):
        self._load()
        return self.rawgroup.desired_capacity

    @property
    def health_check_period(self):
        self._load()
        return self.rawgroup.health_check_period

    @property
    def health_check_type(self):
        self._load()
        return self.rawgroup.health_check_type

    @property
    def launch_config(self):
        self._load()
        return self.rawgroup.launch_config_name

    @property
    def load_balancers(self):
        self._load()
        return self.rawgroup.load_balancers

    @property
    def min_size(self):
        self._load()
        return self.rawgroup.min_size

    @property
    def max_size(self):
        self._load()
        return self.rawgroup.max_size

    @property
    def placement_group(self):
        self._load()
        return self.rawgroup.placement_group

    @property
    def subnets(self):
        self._load()
        subnets = list()
        for s in self.rawgroup.vpc_zone_identifier.split(','):
            subnets.append(s)
        return subnets

    @property
    def tags(self):
        self._load()
        tags = list()
        for t in self.rawgroup.tags:
            tags.append({t.key: t.value})
        return tags

    @property
    def instances(self):
        self._load()
        instances = list()
        for i in self.rawgroup.instances:
            instances.append({
                'id': i.instance_id,
                'health': i.health_status,
                'config': i.launch_config_name,
                'state': i.lifecycle_state,
                'zone': i.availability_zone
            })
        return instances
