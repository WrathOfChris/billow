from . import asg
import billow
import boto

class billowInstance(object):
    """
    Representation of an Instance

    States:
    - Instance: (pending|running|shutting-down|terminated|stopping|stopped)
    - Group:    (Pending|InService|Standby|Terminating|Terminated|
                 Pending:Wait|Pending:Proceed|
                 Terminating:Wait|Terminating:Proceed)
    - Health:   (Healthy|UnHealthy)
    - Balancer: (InService|OutOfService|Unknown)
    """

    def __init__(self, instance_id, region='us-east-1'):
        self.id = instance_id
        self.region = region

        # Group
        self.group_health = None
        self.group_state = None
        self.group_config = None
        self.zone = None

        # Instance
        self.architecture = None
        self.instance_type = None
        self.image_id = None
        self.key_name = None
        self.instance_state = None
        self.instance_state_code = None
        self.launch_time = None
        self.virtualization_type = None
        self.tags = dict()
        self.groups = list()
        # Future: self.cpu = None
        # Future: self.memory = None

        # Instance Network
        self.public_dns_name = None
        self.private_dns_name = None
        self.public_ip_address = None
        self.private_ip_address = None
        self.subnet_id = None
        self.vpc_id = None

        # AWS Specific
        self.aws_ebs_optimized = None

        ## SFL Specific
        # self.sfl_global_identifier = None
        # self.sfl_uuid = None

        # Balancer
        self.balancer_state = None
        self.balancer_reason = None

        # Status
        self.hardware_status = None
        self.hardware_reachability = None
        self.instance_status = None
        self.instance_reachability = None
        self.status_events = None

    def __iter__(self):
        return vars(self).iteritems()

    def __getitem__(self, item):
        return self.__dict__[item]

    def __str__(self):
        return str(self.id)

    def __repr__(self):
        return str(self.id)

    def __eq__(self, other):
        """
        Match strings against 2 forms of instance name:
        1. instance_id:region
        2. instance_id
        """
        if isinstance(other, str) or isinstance(other, unicode):
            if '%s:%s' % (self.id, self.region) == other:
                return True
            return self.id == other
        return self.id == other.id and \
            self.region == other.region

    def push_group_info(self, instance):
        """
        instance is boto.ec2.autoscale.Instance
        """
        if not isinstance(instance, boto.ec2.autoscale.Instance):
            raise TypeError
        self.group_health = instance.health_status
        self.group_state = instance.lifecycle_state
        self.group_config = instance.launch_config_name
        self.zone = instance.availability_zone

    def push_instance_info(self, instance):
        """
        instance is boto.ec2.Instance
        """
        if not isinstance(instance, boto.ec2.instance.Instance):
            raise TypeError
        self.architecture = instance.architecture
        self.aws_ebs_optimized = instance.ebs_optimized
        self.public_dns_name = instance.public_dns_name
        self.private_dns_name = instance.private_dns_name
        self.image_id = instance.image_id
        self.instance_type = instance.instance_type
        self.public_ip_address = instance.ip_address
        self.private_ip_address = instance.private_ip_address
        self.key_name = instance.key_name
        self.launch_time = instance.launch_time
        self.instance_state = instance.state
        self.instance_state_code = instance.state_code
        self.subnet_id = instance.subnet_id
        self.virtualization_type = instance.virtualization_type
        self.vpc_id = instance.vpc_id

        if instance.instance_profile and 'arn' in instance.instance_profile:
            self.instance_profile = instance.instance_profile['arn']

        if instance.tags:
            self.tags = dict()
            for tname, tvalue in instance.tags.iteritems():
                self.tags[tname] = tvalue

        self.groups = list()
        for g in instance.groups:
            self.groups.append(g.id)

    def push_balancer_info(self, instance):
        """
        instance is boto.ec2.elb.instancestate.InstanceState
        """
        if not isinstance(instance, boto.ec2.elb.instancestate.InstanceState):
            raise TypeError
        self.balancer_state = instance.state
        self.balancer_reason = instance.reason_code

    def push_status_info(self, status):
        """
        instance is boto.ec2.instancestatus.InstanceStatus

        code:
            instance-reboot | instance-retirement | instance-stop
            system-reboot | system-maintenance
        """
        if not isinstance(status, boto.ec2.instancestatus.InstanceStatus):
            raise TypeError
        self.hardware_status = status.system_status.status
        self.hardware_reachability = \
                status.system_status.details['reachability']
        self.instance_status = status.instance_status.status
        self.instance_reachability = \
                status.instance_status.details['reachability']
        self.status_events = list()
        if status.events:
            for e in status.events:
                event = {
                        'code': e.code,
                        'description': e.description,
                        'not_before': e.not_before,
                        'not_after': e.not_after
                        }
                self.status_events.append(event)
