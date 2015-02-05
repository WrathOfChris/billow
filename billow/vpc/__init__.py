"""
billow Virtual Private Cloud API
"""
import billow
from billow import aws
import boto
import boto.vpc


class vpc(object):

    def __init__(self, region):
        self.region = region
        self.aws = aws.aws()
        self.vpc = None

    def __connect(self):
        if not self.vpc:
            self.vpc = boto.vpc.connect_to_region(
                self.region,
                aws_access_key_id=self.aws.access_key(),
                aws_secret_access_key=self.aws.secret_key()
            )

    def get_subnet(self, subnets):
        """
        get Subnets in a region
        """
        snets = list()
        self.__connect()

        if not isinstance(subnets, list):
            subnets = [subnets]

        s = self.aws.wrap(
            self.vpc.get_all_subnets,
            subnet_ids=subnets
        )
        snets.extend(s)

        return snets

    def subnet_name(self, subnet):
        subnets = self.get_subnet(subnet)
        if subnets:
            return subnets[0].cidr_block
        return subnet
