from . import asg
from . import dns
from . import elb
from . import sec
import boto
import datetime
import billow


class billowBalancer(object):

    """
    Load Balancer fronting a Group
    """

    def __init__(self, name, region='us-east-1', parent=None):
        self.__name = name
        self.region = region
        self.rawelb = None
        self.rawsgroups = None
        self.rawattrs = None
        self.rawhealth = None
        self.parent = parent
        self.update_time = None

        # Backends
        if self.parent:
            self.elb = self.parent.elb
            self.sec = self.parent.sec
            self.vpc = self.parent.vpc
        else:
            self.elb = elb.elb(self.region)
            self.sec = sec.sec(self.region)
            self.vpc = vpc.vpc(self.region)

    def config(self):
        self.__load()

        self.__config = dict()
        elb = self.__config
        e = self.rawelb

        elb['name'] = self.name
        elb['groups'] = list()
        for sg in self.security_groups:
            elb['groups'].append(self.sg_name(sg, request=True))
        if e.source_security_group:
            elb['source_group'] = e.source_security_group.name
        elb['zones'] = list()
        for z in e.availability_zones:
            elb['zones'].append(z)
        elb['health'] = dict()
        elb['health']['timeout'] = e.health_check.timeout
        elb['health']['target'] = e.health_check.target
        elb['health']['healthy'] = e.health_check.healthy_threshold
        elb['health']['unhealthy'] = e.health_check.unhealthy_threshold
        if e.scheme == u'internal':
            elb['internal'] = True
        elb['subnets'] = list()
        for s in e.subnets:
            elb['subnets'].append(self.vpc.subnet_name(s))

        elb['policies'] = dict()
        if e.policies.app_cookie_stickiness_policies:
            elb['policies'][
                'app_cookie'] = e.policies.app_cookie_stickiness_policies.policy_name
        if e.policies.lb_cookie_stickiness_policies:
            elb['policies'][
                'lb_cookie'] = e.policies.lb_cookie_stickiness_policies.policy_name
        if e.policies.other_policies:
            elb['policies']['other'] = list()
            for p in e.policies.other_policies:
                elb['policies']['other'].append(p.policy_name)

        elb['listeners'] = list()
        for l in e.listeners:
            listener = {
                'from': l.load_balancer_port,
                'to': l.instance_port,
                'from_prot': l.protocol,
                'to_prot': l.instance_protocol
            }
            if l.ssl_certificate_id:
                listener['cert'] = self.lb_certname(l.ssl_certificate_id)
            elb['listeners'].append(listener)

        elb['options'] = self.options

        return self.__config

    def info(self):
        self.__info = self.config()
        self.__info['dns_name'] = self.rawelb.dns_name

        return self.__info

    def __repr__(self):
        """
        billowBalancer(name:region)
        """
        return 'billowGroup(%s:%s)' % (self.name, self.region)

    def __str__(self):
        """
        group
        """
        return '%s' % (self.name)

    def __unicode__(self):
        """
        group
        """
        return u'%s' % (self.name)

    def __eq__(self, other):
        """
        Match strings against 2 forms of balancer name:
        1. balancer:region
        2. balancer
        """
        if isinstance(other, str) or isinstance(other, unicode):
            if "%s:%s" % (self.name, self.region) == other:
                return True
            return self.name == other
        return self.name == other.name and \
            self.region == other.region

    def __load(self, refresh=False):
        if not self.rawelb or refresh:
            elbs = self.elb.get_elb(self.__name)
            if elbs:
                self.rawelb = elbs[0]

    def __load_sgroups(self, refresh=False):
        if not self.rawsgroups or refresh:
            self.__load()
            self.rawsgroups = self.sec.get_groups(self.rawelb.security_groups)

    def __load_attrs(self, refresh=False):
        if not self.rawattrs or refresh:
            self.__load()
            self.rawattrs = self.elb.get_elb_attr(self.__name)

    def __load_health(self, refresh=False):
        if not self.rawhealth or refresh:
            self.__load()
            self.rawhealth = self.elb.get_health(self.__name)

    def refresh(self):
        self.__load(refresh=True)
        self.__load_sgroups(refresh=True)
        self.__load_attrs(refresh=True)
        self.__load_health(refresh=True)

    def lb_certname(self, cert):
        return cert.split('/')[-1]

    def sg_name(self, sgid, request=False):
        self.__load_sgroups()
        for sg in self.rawsgroups:
            if sg.id == sgid:
                return str(sg.name)
        if request:
            sg = self.sec.get_groups(sgid)
            if sg:
                self.rawsgroups.append(sg[0])
                return str(sg[0].name)
        return str(sgid)

    @property
    def name(self):
        self.__load()
        if self.rawelb:
            return self.rawelb.name
        else:
            return self.__name

    @property
    def security_groups(self):
        self.__load()
        if not self.rawelb:
            return list()
        sgroups = list()
        for g in self.rawelb.security_groups:
            sgroups.append(g)
        return sgroups

    @property
    def options(self):
        self.__load_attrs()
        options = {
                'crosszone': self.rawattrs.cross_zone_load_balancing.enabled,
                'idletimeout': self.rawattrs.connecting_settings.idle_timeout,
                'draining': {
                    'enabled': self.rawattrs.connection_draining.enabled,
                    'timeout': self.rawattrs.connection_draining.timeout
                    },
                'accesslog': {
                    'enabled': self.rawattrs.access_log.enabled,
                    's3_bucket_name': self.rawattrs.access_log.s3_bucket_name,
                    's3_bucket_prefix': \
                            self.rawattrs.access_log.s3_bucket_prefix,
                    'emit_interval': self.rawattrs.access_log.emit_interval
                    }
                }
        return options

    @property
    def zones(self):
        self.__load()
        zonelist = list()
        for z in self.rawelb.availability_zones:
            zonelist.append(z)
        return zonelist

    @property
    def instances(self):
        self.__load_health()
        instances = list()
        for h in self.rawhealth:
            inst = billow.billowInstance(h.instance_id, region=self.region)
            inst.push_balancer_info(h)
            instances.append(inst)
        return instances

    def deregister(self, instance_id):
        if instance_id not in self.instances:
            print "XXX instance not found in balancer"
            return False
        ret = self.elb.deregister(self.name, instance_id)
        # XXX ret is instance list of current instances
        # XXX update instancelist?
        return True

    def register(self, instance_id):
        if instance_id in self.instances:
            print "XXX instance already exists in balancer"
            return False
        ret = self.elb.register(self.name, instance_id)
        return ret

    @property
    def health_target(self):
        self.__load()
        return self.rawelb.health_check.target

    @property
    def health_timeout(self):
        self.__load()
        return self.rawelb.health_check.timeout

    @property
    def health_threshold(self):
        self.__load()
        return self.rawelb.health_check.healthy_threshold

    @property
    def health_unhealthy_threshold(self):
        self.__load()
        return self.rawelb.health_check.unhealthy_threshold

    @property
    def connection_draining(self):
        self.__load()
        self.__load_attrs()
        return self.rawattrs.connection_draining.enabled

    @property
    def connection_draining_timeout(self):
        self.__load()
        self.__load_attrs()
        return self.rawattrs.connection_draining.timeout

    @property
    def dns_name(self):
        self.__load()
        return self.rawelb.dns_name
