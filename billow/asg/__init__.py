"""
billow AutoScaleGroup API
"""
import billow
from billow import aws
import boto
import boto.ec2
import boto.ec2.autoscale

class asg():
    def __init__(self, region):
        self.region = region
        self.aws = aws.aws()
        self.asg = None

    def _connect(self):
        if not self.asg:
            self.asg = boto.ec2.autoscale.connect_to_region(
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
        self._connect()

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
        self._connect()

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
        self._connect()

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
        self._connect()

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
