from . import asg
import boto
import datetime
import re


class billowImage(object):

    """
    Group Image

    AMI on Amazon
    """

    def __init__(self, region='us-east-1', parent=None):
        self.region = region
        self.parent = parent

        if self.parent:
            self.asg = self.parent.asg
        else:
            self.asg = asg.asg(self.region)

    def find_by_name(self, name, amis):
        for a in amis:
            if str(a.name) == name:
                return a
            if re.match("%s-\d{14}" % name, str(a.name)):
                return a
        return None

    def search(self, service, environ):
        """
        Search ami list, find best match:
        1. {{environ}}-{{service}}-{{date}}
        2. all-{{service}}-{{date}}
        3. {{service}}-{{date}}
        4. {{service}}
        """
        formats = [
                ('%s-%s-*' % (environ, service), '%s-%s' % (environ, service)),
                ('all-%s-*' % service, 'all-%s' % service),
                ('%s-*' % service, service)
                ]

        for f, m in formats:
            ami = None
            amis = self.asg.get_images_byname(f)
            if amis:
                amis = sorted(amis, key=lambda a: a.name, reverse=True)
                ami = self.find_by_name(m, amis)

            if ami:
                return ami

        # 4. {{service}}
        amis = self.asg.get_images_byname(service)
        if amis:
            return amis[0]

        return None

    def list(self, service, environ):
        """
        List ami list, order by best match:
        1. {{environ}}-{{service}}-{{date}}
        2. all-{{service}}-{{date}}
        3. {{service}}-{{date}}
        4. {{service}}
        """
        formats = [
                ('%s-%s-*' % (environ, service), '%s-%s' % (environ, service)),
                ('all-%s-*' % service, 'all-%s' % service),
                ('%s-*' % service, service)
                ]
        amilist = list()

        for f, m in formats:
            ami = None
            amis = self.asg.get_images_byname(f)
            if amis:
                amilist.extend(sorted(amis, key=lambda a: a.name, reverse=True))

        # 4. {{service}}
        amis = self.asg.get_images_byname(service)
        if amis:
            amilist.extend(amis)

        return amilist
