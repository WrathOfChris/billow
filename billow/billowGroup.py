from . import asg
from . import dns
from . import elb
from . import sec
import boto
import datetime


class billowGroup(object):

    """
    a large undulating mass of cloud services
    """

    def __init__(self, group, region='us-east-1', parent=None):
        self.group = group
        self.rawgroup = None
        self.rawconfig = None
        self.rawsgroups = None
        self.__region = region
        self.__service = None
        self.__environ = None
        self.__cluster = None
        self.parent = parent
        self.update_time = None

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
        self.tagenviron = 'env'
        self.tagcluster = 'cluster'

    def config(self):
        self.__config = dict()
        self.__config['name'] = self.name
        if self.region != self.parent.region:
            self.__config['region'] = self.region
        if self.service != self.parent.service:
            self.__config['service'] = self.service
        if self.environ != self.parent.environ:
            self.__config['environ'] = self.environ
        if self.cluster and self.cluster != self.parent.cluster:
            self.__config['cluster'] = self.cluster

        self.__config['load_balancers'] = self.load_balancers

        self.__config['size'] = dict()
        self.__config['size']['cur'] = self.cur_size
        self.__config['size']['min'] = self.min_size
        self.__config['size']['max'] = self.max_size

        self.__config['subnets'] = self.subnets
        self.__config['public'] = self.public
        if self.placement_group:
            self.__config['placement_group'] = self.placement_group
        if self.suspended_processes:
            self.__config['suspended_processes'] = self.suspended_processes

        self.__config['health'] = dict()
        self.__config['health']['check_period'] = self.health_check_period
        self.__config['health']['check_type'] = self.health_check_type

        self.__config['config'] = dict()
        self.__config['config']['name'] = self.launch_config
        self.__config['config']['ami'] = self.config_ami
        self.__config['config']['type'] = self.config_type
        if self.config_userdata:
            self.__config['config']['userdata'] = self.config_userdata
        if self.config_keypair:
            self.__config['config']['keypair'] = self.config_keypair
        if self.config_role:
            self.__config['config']['role'] = self.config_role

        self.__config['security'] = dict()
        self.__config['security']['groups'] = self.security_groups
        self.__config['security']['rules'] = self.security_rules

        return self.__config

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

            # preserve update time for future caching decisions
            self.update_time = datetime.datetime.utcnow()

        for t in self.rawgroup.tags:
            if t.key == self.tagservice:
                self.__service = t.value
            elif t.key == self.tagenviron:
                self.__environ = t.value
            elif t.key == self.tagcluster:
                self.__cluster = t.value

    def _load_config(self):
        if not self.rawconfig:
            config = self.asg.get_configs(self.launch_config)
            if len(config) == 1:
                self.rawconfig = config[0]

    def _load_sgroups(self):
        if not self.rawsgroups:
            self.rawsgroups = self.sec.get_groups(self.security_groups)

    def push(self, rawgroup):
        """
        Allow premature optimization by pushing in the ASG if it has been
        gathered elsewhere
        """
        self.rawgroup = rawgroup
        self._load()

    def refresh(self):
        self.rawgroup = None
        self._load()

    @property
    def region(self):
        if self.parent:
            return self.parent.region
        else:
            return self.__region

    @property
    def service(self):
        if self.parent:
            return self.parent.service
        else:
            self._load()
            return self.__service

    @property
    def environ(self):
        if not self.__environ:
            self._load()
        return self.__environ

    @property
    def cluster(self):
        if not self.__cluster:
            self._load()
        return self.__cluster

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
    def config_ami(self):
        self._load_config()
        return self.rawconfig.image_id

    @property
    def config_type(self):
        self._load_config()
        return self.rawconfig.instance_type

    @property
    def config_userdata(self):
        self._load_config()
        return self.rawconfig.user_data

    @property
    def config_keypair(self):
        self._load_config()
        return self.rawconfig.key_name

    @property
    def config_role(self):
        self._load_config()
        return self.rawconfig.instance_profile_name

    @property
    def load_balancers(self):
        self._load()
        elbs = list()
        for lb in self.rawgroup.load_balancers:
            elbs.append(lb)
        return elbs

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

    @property
    def arn(self):
        self._load()
        return self.rawgroup.autoscaling_group_arn

    @property
    def suspended_processes(self):
        self._load()
        suspended_processes = list()
        for sp in self.rawgroup.suspended_processes:
            suspended_processes.append(sp.process_name)
        return suspended_processes

    @property
    def security_groups(self):
        self._load_config()
        sgroups = list()
        for sg in self.rawconfig.security_groups:
            sgroups.append(sg)
        return sgroups

    @property
    def security_rules(self):
        self._load_config()
        self._load_sgroups()
        srules = list()
        for sg in self.rawsgroups:
            for sr in sg.rules:
                rule = dict()
                rule['name'] = sg.name
                rule['id'] = sg.id
                rule['from_port'] = sr.from_port
                if sr.grants:
                    rule['grants'] = list()
                    for grant in sr.grants:
                        if grant.cidr_ip:
                            rule['grants'].append(grant.cidr_ip)
                        if grant.group_id:
                            rule['grants'].append(grant.group_id)
                rule['ip_protocol'] = sr.ip_protocol
                rule['to_port'] = sr.to_port
                srules.append(rule)
        return srules

    @property
    def public(self):
        self._load_config()
        return self.rawconfig.associate_public_ip_address

    # addrs
    # aminame
    # security group names
    # subnets by address
    # ports
    # pubports
    # allow {cidr_ip: 172.16.0.0/12, from_port: 22, ip_protocol: tcp, to_port: 22}
    #       { from: 9090, to: 9090, group: 'payments-prod', prot: tcp }
    # egress
    # extports
    # intaddrs
