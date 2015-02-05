"""
billow Security API
"""
import billow
from billow import aws
import boto
import boto.ec2


class sec(object):

    def __init__(self, region):
        self.region = region
        self.aws = aws.aws()
        self.ec2 = None
        self.account_id = None

    def __connect(self):
        if not self.ec2:
            self.ec2 = boto.ec2.connect_to_region(
                self.region,
                aws_access_key_id=self.aws.access_key(),
                aws_secret_access_key=self.aws.secret_key()
            )

    def get_account_id(self):
        if not self.account_id:
            iam = boto.connect_iam()
            self.account_id = iam.get_user()['get_user_response']['get_user_result'][
                'user']['arn'].split(':')[4]
        return self.account_id

    def get_groups(self, groups):
        """
        get SecurityGroups in a region
        """
        sgroups = list()
        self.__connect()

        if not isinstance(groups, list):
            groups = [groups]

        a = self.aws.wrap(
            self.ec2.get_all_security_groups,
            group_ids=groups
        )
        sgroups.extend(a)

        return sgroups

    def find_group(self, name, vpcid=None):
        """
        find SecurityGroups in a region
        """
        sgroups = list()
        self.__connect()

        sgfilter = { 'group-name': name }
        if vpcid:
            sgfilter['vpc_id'] = vpcid

        s = self.aws.wrap(
            self.ec2.get_all_security_groups,
            filters=sgfilter
        )
        sgroups.extend(s)

        return sgroups
