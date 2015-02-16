from . import asg
from . import dns
from . import elb
from . import sec
from . import vpc
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
        self.balancers = list()

        self.rawsgroups = None
        self.rawelbs = None

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
            self.vpc = self.parent.vpc
        else:
            self.asg = asg.asg(self.region)
            self.dns = dns.dns(self.region)
            self.elb = elb.elb(self.region)
            self.sec = sec.sec(self.region)
            self.vpc = vpc.vpc(self.region)

        self.tagservice = 'service'

    def config(self):
        self.__config = dict()
        self.__config[self.service] = dict()
        c = self.__config[self.service]
        c['region'] = self.region
        c['service'] = self.service
        c['environ'] = self.environ
        if self.cluster:
            c['cluster'] = self.cluster

        c['groups'] = list()
        for g in self.groups:
            c['groups'].append(g.config())

        c['security'] = dict()
        c['security']['groups'] = list()
        for sg in self.security_groups:
            c['security']['groups'].append(self.sg_name(sg, request=True))
        c['security']['rules'] = self.security_rules

        self.__load_elbs()
        c['load_balancers'] = dict()
        for e in self.rawelbs:
            c['load_balancers'][str(e.name)] = dict()
            elb = c['load_balancers'][str(e.name)]
            elb['groups'] = list()
            for sg in e.security_groups:
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

            attrs = self.elb.get_elb_attr(e.name)
            if attrs:
                if attrs.cross_zone_load_balancing:
                    if 'options' not in elb:
                        elb['options'] = dict()
                    elb['options']['crosszone'] = bool(attrs.cross_zone_load_balancing)
                if attrs.connecting_settings.idle_timeout != self.elb.default_idle_timeout:
                    if 'options' not in elb:
                        elb['options'] = dict()
                    elb['options']['idletimeout'] = int(
                        attrs.connecting_settings.idle_timeout)
                # elb['options']['draining']
                # elb['options']['accesslog']

        return self.__config

    def info(self):
        self.__info = self.config()

        for e in self.rawelbs:
            self.__info[self.service]['load_balancers'][str(e.name)]['dns_name'] = e.dns_name

        self.__info[self.service]['groups'] = list()
        for g in self.groups:
            self.__info[self.service]['groups'].append(g.info())

        return self.__info

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

    def __load_sgroups(self):
        if not self.rawsgroups:
            self.rawsgroups = self.sec.get_groups(self.security_groups)

    def __load_elbs(self):
        if not self.rawelbs:
            # Never query an empty list of ELBs
            if self.load_balancers:
                self.rawelbs = self.elb.get_elb(self.load_balancers)
            else:
                self.rawelbs = list()

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
        ami = None
        for g in self.groups:
            if not ami:
                ami = g.ami
            if ami != g.ami:
                return None
        return ami

    @property
    def security_groups(self):
        self.__load_elbs()
        sgroups = list()
        for g in self.groups:
            sgroups.extend(x for x in g.security_groups if x not in sgroups)
        for e in self.rawelbs:
            sgroups.extend(x for x in e.security_groups if x not in sgroups)
        return sgroups

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
    def security_rules(self):
        self.__load_sgroups()
        srules = dict()
        for sg in self.rawsgroups:
            if sg.id not in self.security_groups:
                continue
            sg_name = self.sg_name(sg.id)
            if sg_name not in srules:
                srules[sg_name] = list()
            for sr in sg.rules:
                rule = dict()
                rule['from_port'] = sr.from_port
                if sr.grants:
                    for grant in sr.grants:
                        if grant.cidr_ip:
                            rule['cidr'] = grant.cidr_ip
                        if grant.group_id:
                            rule['group'] = self.sg_name(grant.group_id,
                                                         request=True)
                rule['ip_protocol'] = sr.ip_protocol
                rule['to_port'] = sr.to_port
                srules[sg_name].append(rule)
        return srules

    @property
    def load_balancers(self):
        elbs = list()
        for g in self.groups:
            elbs.extend(x for x in g.load_balancers if x not in elbs)
        return elbs

    def lb_certname(self, cert):
        return cert.split('/')[-1]

    def get_instance(self, instance):
        for g in self.groups:
            i = g.get_instance(instance)
            if i:
                return i
        return None
