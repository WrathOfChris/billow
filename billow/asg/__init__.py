"""
billow AutoScaleGroup API
"""
import billow
from billow import aws
import boto
import boto.ec2
import boto.ec2.autoscale
import time
import fnmatch
import re


class asg(object):

    def __init__(self, region):
        self.region = region
        self.aws = aws.aws()
        self.asg = None
        self.ec2 = None
        self.cachetime = 60
        self.__lc_find_cache_time = time.time()
        self.__lc_find_cache = None

    def __connect(self):
        if not self.asg:
            self.asg = boto.ec2.autoscale.connect_to_region(
                self.region,
                aws_access_key_id=self.aws.access_key(),
                aws_secret_access_key=self.aws.secret_key()
            )

    def __connect_ec2(self):
        if not self.ec2:
            self.ec2 = boto.ec2.connect_to_region(
                self.region,
                aws_access_key_id=self.aws.access_key(),
                aws_secret_access_key=self.aws.secret_key()
            )

    def list_groups(self):
        """
        list all AutoScaleGroups in a region
        """
        self.asgs = list()
        marker = None
        self.__connect()

        while True:
            asgs = self.aws.wrap(
                self.asg.get_all_groups,
                next_token=marker
            )
            self.asgs.extend(asgs)
            if asgs.next_token:
                marker = asgs.next_token
            else:
                break

        return self.asgs

    def list_tags(self, name=None, tag=None, value=None):
        """
        list all AutoScaleGroups with a specific tag in a region
        """
        self.tags = list()
        marker = None
        self.__connect()

        filters = None
        if name or tag or value:
            filters = dict()
        if name:
            filters['auto-scaling-group'] = name
        if tag:
            filters['key'] = tag
        if value:
            filters['value'] = value

        while True:
            tags = self.aws.wrap(
                self.asg.get_all_tags,
                filters=filters,
                next_token=marker
            )
            self.tags.extend(tags)
            if tags.next_token:
                marker = tags.next_token
            else:
                break

        return self.tags

    def list_configs(self):
        """
        list all LaunchConfigurations a region
        """
        self.lcs = list()
        marker = None
        self.__connect()

        while True:
            lcs = self.aws.wrap(
                self.asg.get_all_launch_configurations,
                next_token=marker
            )
            self.lcs.extend(lcs)
            if lcs.next_token:
                marker = lcs.next_token
            else:
                break

        return self.lcs

    def get_groups(self, groups):
        """
        get AutoScaleGroup in a region
        """
        asgs = list()
        marker = None
        self.__connect()

        if not isinstance(groups, list):
            groups = [groups]

        while True:
            a = self.aws.wrap(
                self.asg.get_all_groups,
                names=groups,
                next_token=marker
            )
            asgs.extend(a)
            if a.next_token:
                marker = a.next_token
            else:
                break

        return asgs

    def get_configs(self, names):
        """
        get LaunchConfigurations in a region
        """
        configs = list()
        marker = None
        self.__connect()

        if not isinstance(names, list):
            names = [names]

        while True:
            a = self.aws.wrap(
                self.asg.get_all_launch_configurations,
                names=names,
                next_token=marker
            )
            configs.extend(a)
            if a.next_token:
                marker = a.next_token
            else:
                break

        return configs

    def get_instance(self, instance_ids):
        """
        get Instances in a region
        """
        instances = list()
        marker = None
        self.__connect_ec2()

        if not isinstance(instance_ids, list):
            instance_ids = [instance_ids]

        while True:
            #
            # Use get_all_reservations() since get_only_instances does not
            # support next_token for rate-limiting
            #
            reservations = self.aws.wrap(
                self.ec2.get_all_reservations,
                instance_ids=instance_ids,
                next_token=marker
            )
            for r in reservations:
                for i in r.instances:
                    instances.append(i)
            if reservations.next_token:
                marker = reservations.next_token
            else:
                break

        return instances

    def get_instance_status(self, instance_ids, filters=None):
        """
        get Instance Status' in a region
        """
        statuses = list()
        marker = None
        self.__connect_ec2()

        if not isinstance(instance_ids, list):
            instance_ids = [instance_ids]

        while True:
            s = self.aws.wrap(
                self.ec2.get_all_instance_status,
                instance_ids=instance_ids,
                include_all_instances=True,
                filters=filters,
                next_token=marker
            )
            statuses.extend(s)
            if s.next_token:
                marker = s.next_token
            else:
                break

        return statuses

    def match_images_name(self, name):
        """
        match Images in a region.

        An asterisk (*) matches zero or more characters, and a question mark
        (?) matches exactly one character.
        http://docs.aws.amazon.com/AWSEC2/latest/CommandLineReference/ApiReference-cmd-DescribeImages.html
        """
        images = list()
        self.__connect_ec2()
        amifilter = {'name': name}

        images = self.aws.wrap(
            self.ec2.get_all_images,
            filters=amifilter
        )

        return images

    def match_images_tags(self, tags):
        """
        get Images in a region
        tags = { 'key': value, 'key2': value2 }
        """
        images = list()
        self.__connect_ec2()

        amifilter = list()
        for k, v in tags.iteritems():
            f = {'tag:%s' % k, v}
            amifilter.append(f)

        images = self.aws.wrap(
            self.ec2.get_all_images,
            filters=amifilter
        )

        return images

    def cache_configs(self):
        """
        There is no API for this, so implement a simple cache to preserve the
        full list of LaunchConfigs since this can be a heavy call.
        """
        if self.__lc_find_cache and (self.__lc_find_cache_time +
                                     self.cachetime) < time.time():
            self.__lc_find_cache = None

        if not self.__lc_find_cache:
            self.__lc_find_cache = list()
            marker = None
            self.__connect()

            while True:
                lcs = self.aws.wrap(
                    self.asg.get_all_launch_configurations,
                    next_token=marker
                )
                self.__lc_find_cache.extend(lcs)
                if lcs.next_token:
                    marker = lcs.next_token
                else:
                    break

    def regex_configs(self, regex):
        """
        find LaunchConfigurations by regex.
        """
        self.cache_configs()

        configs = list()
        for lc in self.__lc_find_cache:
            if re.match(regex, lc.name):
                configs.append(lc)

        return configs

    def match_configs(self, match):
        """
        find LaunchConfigurations by fnmatch
        """
        self.cache_configs()

        configs = list()
        for lc in self.__lc_find_cache:
            if fnmatch.fnmatch(lc.name, match):
                configs.append(lc)

        return configs

    def terminate(self, instance_id, decrement_capacity=True):
        """
        Terminate instance within an asg object
        """

        ret = self.aws.wrap(
            self.asg.terminate_instance,
            instance_id=instance_id,
            decrement_capacity=decrement_capacity
        )

        return ret

    def set_capacity(self, group_name, desired_capacity, honor_cooldown=False):
        """
        Set Desired Capacity for an AutoScaleGroup
        """

        ret = self.aws.wrap(
            self.asg.set_desired_capacity,
            group_name=group_name,
            desired_capacity=desired_capacity,
            honor_cooldown=honor_cooldown
        )

        return ret

    def disassociate_address(self, association_id):
        """
        Disassociate an address from an instance
        """

        ret = self.aws.wrap(
            self.ec2.disassociate_address,
            association_id=association_id
            )

        return ret

    def associate_address(self, allocation_id, instance_id=None,
            network_interface_id=None, allow_reassociation=False):
        """
        Associate an address to an instance
        """

        # When using an Allocation ID, make sure to pass None for public_ip
        ret = self.aws.wrap(
            self.ec2.associate_address,
            public_ip=None,
            allocation_id=allocation_id,
            instance_id=instance_id,
            network_interface_id=network_interface_id,
            allow_reassociation=allow_reassociation
            )

        return ret

    def unassign_private_ip_addresses(self, network_interface_id=None,
            private_ip_addresses=None):
        """
        UnAssign a private address from an instance
        """

        ret = self.aws.wrap(
            self.ec2.unassign_private_ip_addresses,
            network_interface_id=None,
            private_ip_addresses=None
            )

        return ret

    def assign_private_ip_addresses(self, network_interface_id=None,
            private_ip_addresses=None, allow_reassignment=False):
        """
        Assign a private address to an instance
        """

        ret = self.aws.wrap(
            self.ec2.assign_private_ip_addresses,
            network_interface_id=None,
            private_ip_addresses=None,
            allow_reassignment=False
            )

        return ret

    def list_activities(self, group, max_records=None):
        """
        list all AutoScaleGroup activities
        """
        self.activities = list()
        marker = None
        self.__connect()

        while True:
            activities = self.aws.wrap(
                self.asg.get_all_activities,
                autoscale_group=group,
                max_records=max_records,
                next_token=marker
            )
            self.activities.extend(activities)
            if activities.next_token:
                marker = activities.next_token
            else:
                break

        return self.activities

    def get_addresses(self, ip_addresses):
        """
        get Addresses
        """
        self.__connect_ec2()

        if not isinstance(ip_addresses, list):
            ip_addresses = [ip_addresses]

        addrs = self.aws.wrap(
            self.ec2.get_all_addresses,
            addresses=ip_addresses
        )

        return addrs
