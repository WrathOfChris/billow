from . import asg
from . import dns
from . import elb
from . import sec
import boto
import pprint


class billowService():

    """
    a large undulating mass of cloud services
    """

    def __init__(self, service, groups=[], region='us-east-1', environ=None):
        self.service = service
        self.environ = environ
        self.groups = groups
        self.region = region

    def __repr__(self):
        """
        {'groups': [u'example-stage'],
         'region': 'us-east-1',
         'service': u'example',
         'environ': u'stage'}
        """
        return pprint.pformat({
            'service': self.service,
            'groups': self.groups,
            'region': self.region,
            'environ': self.environ})

    def __str__(self):
        """
        service-env:region
        """
        return "%s-%s:%s" % (self.service, self.environ, self.region)

    def __eq__(self, other):
        return self.service == other.service and \
            self.environ == other.environ and \
            self.region == other.region

    def startElement(self, name, attrs):
        if name == 'service':
            return self.service
        elif name == 'groups':
            return self.groups
        elif name == 'region':
            return self.region
        elif name == 'environ':
            return self.environ
        else:
            return

    def endElement(self, name, value):
        if name == 'service':
            self.service = value
        elif name == 'groups':
            self.groups = value
        elif name == 'region':
            self.region = value
        elif name == 'environ':
            self.environ = value
        else:
            setattr(self, name, value)
