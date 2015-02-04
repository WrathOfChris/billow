import sys
try:
    import boto
except ImportError:
    sys.stderr.write('boto required\n')
    raise
from boto.exception import BotoServerError
from distutils.version import LooseVersion
import time
import os


class aws(object):

    def __init__(self, delay=0, maxdelay=16):
        self.rate_limit_delay = delay
        self.rate_limit_maxdelay = maxdelay
        # requires unmerged https://github.com/boto/boto/pull/2898
        self.min_boto_version = '2.35.2'
        self.region = 'us-east-1'

        if not self.validate_version(self.min_boto_version):
            sys.stderr.write("boto >= %s required\n" %
                             self.min_boto_version)
            raise ImportError

        # Import ENV vars if available, fall back to IAM instance-profile
        self.aws_access = None
        self.aws_secret = None
        if 'AWS_ACCESS_KEY' in os.environ:
            self.aws_access = os.environ['AWS_ACCESS_KEY']
        if 'AWS_SECRET_KEY' in os.environ:
            self.aws_secret = os.environ['AWS_SECRET_KEY']

    def access_key(self):
        return self.aws_access

    def secret_key(self):
        return self.aws_secret

    def validate_version(self, version):
        if LooseVersion(boto.Version) < LooseVersion(version):
            return False
        return True

    def wrap(self, awsfunc, *args, **nargs):
        """
        Wrap AWS call with Rate-Limiting backoff
        Gratefully taken Netflix/security_monkey
        """
        attempts = 0

        while True:
            attempts = attempts + 1
            try:
                if self.rate_limit_delay > 0:
                    time.sleep(self.rate_limit_delay)

                retval = awsfunc(*args, **nargs)

                if self.rate_limit_delay > 0:
                    self.rate_limit_delay = self.rate_limit_delay / 2

                return retval

            except BotoServerError as e:
                if e.error_code == 'Throttling':
                    if self.rate_limit_delay == 0:
                        self.rate_limit_delay = 1
                        sys.stderr.write('rate-limited: attempt %d\n' %
                                         attempts)
                    elif self.rate_limit_delay < self.rate_limit_maxdelay:
                        self.rate_limit_delay = self.rate_limit_delay * 2
                        sys.stderr.write('rate-limited: attempt %d\n' %
                                         attempts)
                    else:
                        raise e

                elif e.error_code == 'ServiceUnavailable':
                    if self.rate_limit_delay == 0:
                        self.rate_limit_delay = 1
                        sys.stderr.write('api-unavailable: attempt %d\n' %
                                         attempts)
                    elif self.rate_limit_delay < self.rate_limit_maxdelay:
                        self.rate_limit_delay = self.rate_limit_delay * 2
                        sys.stderr.write('api-unavailable: attempt %d\n' %
                                         attempts)
                    else:
                        raise e
                else:
                    raise e

    def instance_info(self):
        identity = boto.utils.get_instance_identity(timeout=60,
                                                    num_retries=5)
        self.info['instanceId'] = identity['document'][u'instanceId']
        self.info['availabilityZone'] = \
            identity['document'][u'availabilityZone']
        self.info['region'] = identity['document'][u'region']
        return self.info
