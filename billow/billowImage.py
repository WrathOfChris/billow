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

    def find_name_regex(self, regex, amis):
        amilist = list()
        for a in amis:
            if str(a.name) == regex:
                amilist.append(a)
                continue
            if re.match(regex, str(a.name)):
                amilist.append(a)
        return amilist

    def search(self, name, regex=None):
        """
        Search ami list, then filter result by regex
        """
        amis = self.asg.match_images_name(name)
        if amis:
            amis = sorted(amis, key=lambda a: a.name, reverse=False)
            if regex:
                return self.find_name_regex(regex, amis)
            return amis

        return list()

    def list_dated_newest(self, service, environ):
        """
        List images, reverse-sorted, in the following order:
        1. {{environ}}-{{service}}-{{date}}
        2. all-{{service}}-{{date}}
        3. {{service}}-{{date}}
        4. {{service}}
        """
        formats = [
            ('%s-%s-*' % (environ, service), '%s-%s-\d{14}' % (environ, service)),
            ('all-%s-*' % service, 'all-%s-\d{14}' % service),
            ('%s-*' % service, service),
            (service, service)
        ]

        amilist = list()
        for f, r in formats:
            amis = self.asg.match_images_name(f)
            if amis:
                amis = sorted(amis, key=lambda a: a.name, reverse=True)
                amilist.extend(self.find_name_regex(r, amis))

        return amilist

    def get_dated_newest(self, service, environ):
        """
        Get single newest image from list, based on postfixed YYYYMMDDHHMMSS
        """
        amilist = self.list_dated_newest(service, environ)
        if amilist:
            return amilist[0]
        return None
