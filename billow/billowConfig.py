from . import asg
import boto
import datetime
import re


class billowConfig(object):

    """
    Group Config

    LaunchConfig on Amazon
    """

    # BLOCK DEVICE MAPPINGS - http://aws.amazon.com/ec2/instance-types/
    blockdevmap = {
        'c1.medium': 1,
        'c1.xlarge': 1,
        'c3.2xlarge': 2,
        'c3.4xlarge': 2,
        'c3.8xlarge': 2,
        'c3.large': 2,
        'c3.xlarge': 2,
        'c4.2xlarge': 0,
        'c4.4xlarge': 0,
        'c4.8xlarge': 0,
        'c4.large': 0,
        'c4.xlarge': 0,
        'cc2.8xlarge': 4,
        'cg1.4xlarge': 2,
        'cr1.8xlarge': 2,
        'g2.2xlarge': 1,
        'hi1.4xlarge': 2,
        'hs1.8xlarge': 24,
        'i2.2xlarge': 2,
        'i2.4xlarge': 4,
        'i2.8xlarge': 8,
        'i2.xlarge': 1,
        'm1.large': 2,
        'm1.medium': 1,
        'm1.small': 1,
        'm1.xlarge': 4,
        'm2.2xlarge': 1,
        'm2.4xlarge': 2,
        'm2.xlarge': 1,
        'm3.2xlarge': 2,
        'm3.large': 1,
        'm3.medium': 1,
        'm3.xlarge': 2,
        't1.micro': 0,
        't2.medium': 0,
        't2.micro': 0,
        't2.small': 0,
    }

    def __init__(self, region='us-east-1', parent=None):
        self.region = region
        self.parent = parent

        if self.parent:
            self.asg = self.parent.asg
        else:
            self.asg = asg.asg(self.region)

    def search(self, regex):
        """
        Search config list by regex
        """
        return self.asg.regex_configs(regex)

    def match(self, match):
        """
        Match configs using fnmatch()
        """
        return self.asg.match_configs(match)

    def list_dated_newest(self, service, environ):
        """
        Search config list, find best match:
        1. {{environ}}-{{service}}-{{date}}
        2. {{service}}-{{date}}
        3. {{service}}
        """
        formats = [
            '%s-%s-\d{14}' % (environ, service),
            '%s-\d{14}' % service,
            service
        ]

        configlist = list()
        for f in formats:
            configs = self.asg.regex_configs(f)
            if configs:
                configs = sorted(configs, key=lambda c: c.name, reverse=True)
                configlist.extend(configs)

        return configlist

    def get_dated_newest(self, service, environ):
        """
        Get single newest config from list, based on postfixed YYYYMMDDHHMMSS
        """
        configlist = self.list_dated_newest(service, environ)
        if configlist:
            return configlist[0]
        return None
