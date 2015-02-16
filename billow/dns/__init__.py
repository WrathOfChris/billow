"""
billow DNS API
"""
import billow
from billow import aws
import boto.route53
import boto.route53.exception
import boto.route53.zone
import boto.sts


class dns(object):

    def __init__(self, region):
        self.region = region
        self.aws = aws.aws()
        self.r53 = None
        self.sts = None
        self.ststok = None
        self.role = None

    def __connect(self, role=None):
        if not self.sts:
            self.sts = boto.sts.connect_to_region(self.region,
                    aws_access_key_id=self.aws.access_key(),
                    aws_secret_access_key=self.aws.secret_key())

        if role:
            if not self.ststok or role != self.role:
                self.role = role
                self.ststok = self.sts.assume_role(role, 'billow')
                self.r53 = boto.connect_route53(
                    aws_access_key_id=self.ststok.credentials.access_key,
                    aws_secret_access_key=self.ststok.credentials.secret_key,
                    security_token=self.ststok.credentials.session_token
                )

        if not self.r53:
            self.r53 = boto.connect_route53(
                aws_access_key_id=self.aws.access_key(),
                aws_secret_access_key=self.aws.secret_key()
            )

    def get_records(self, dnsname, role=None):
        self.__connect(role=role)

        # XXX consider try/catch boto.route53.exception.DNSServerError
        zone = self.aws.wrap(
                self.r53.get_zone,
                dnsname
                )

        if not zone:
            return list()

        # XXX consider try/catch boto.route53.exception.DNSServerError
        zonerecs = self.aws.wrap(
                zone.get_records
                )

        return zonerecs
