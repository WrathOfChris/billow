"""
billow Load Balancer API
"""
import billow
from billow import aws
import boto
import boto.ec2
import boto.ec2.elb


class elb(object):

    def __init__(self, region):
        self.region = region
        self.aws = aws.aws()
        self.elb = None

        self.default_idle_timeout = 60

    def _connect(self):
        if not self.elb:
            self.elb = boto.ec2.elb.connect_to_region(
                self.region,
                aws_access_key_id=self.aws.access_key(),
                aws_secret_access_key=self.aws.secret_key()
            )

    def list_elbs(self):
        """
        list all ELBs in a region
        """
        self.elbs = list()
        marker = None
        self._connect()

        while True:
            elbs = self.aws.wrap(
                self.elb.get_all_load_balancers,
                marker=marker
            )
            self.elbs.extend(elbs)
            if elbs.next_marker:
                marker = elbs.next_marker
            else:
                break

        return self.elbs

    def get_elb(self, names):
        """
        get ELB(s) by name
        """
        if not isinstance(names, list):
            names = [names]

        elbs = list()
        marker = None
        self._connect()

        while True:
            e = self.aws.wrap(
                self.elb.get_all_load_balancers,
                load_balancer_names=names,
                marker=marker
            )
            elbs.extend(e)
            if e.next_marker:
                marker = e.next_marker
            else:
                break

        return elbs

    def get_elb_attr(self, name):
        """
        get ELB attributes by name
        """
        self._connect()

        attr = self.aws.wrap(
            self.elb.get_all_lb_attributes,
            load_balancer_name=name
        )

        return attr
