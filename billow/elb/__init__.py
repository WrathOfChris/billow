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
