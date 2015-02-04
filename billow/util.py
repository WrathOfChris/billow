import argparse


def common_parser(description='untitled'):
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        '-a',
        '--auto',
        help='auto-detect',
        action='store_true'
    )

    parser.add_argument(
        '-r',
        '--region',
        help='ec2 region'
    )

    parser.add_argument(
        '--regions',
        nargs='*',
        help='ec2 regions'
    )

    return parser

import boto.utils


def common_args(args):

    # Region setting:
    # 1. Prefer command-line --region
    # 2. Use instance metadata when --auto
    # 3. Default to us-east-1
    local_region = None
    if args.auto:
        identity = boto.utils.get_instance_identity(timeout=1, num_retries=5)
        try:
            local_region = identity['document']['region']
        except KeyError:
            pass
    if not args.region:
        args.region = local_region
    else:
        local_region = args.region
    if not args.region:
        args.region = 'us-east-1'

    # Region Operations:
    # 1. Use --regions
    # 2. Use above detected region
    # 3. Split any comma-separated regions
    if not args.regions:
        args.regions = args.region
    if not isinstance(args.regions, list):
        args.regions = [args.regions]
    for r in args.regions[:]:
        if ',' in r:
            args.regions.extend(r.split(','))
            args.regions.remove(r)

import signal
import sys
import errno


def cli_signal_handler(signal, frame):
    sys.exit(errno.EINTR)


def catch_sigint():
    signal.signal(signal.SIGINT, cli_signal_handler)

import fnmatch
import re


def regex_match(match, string, use_regex):
    if use_regex and re.match(match, string):
        return True
    elif fnmatch.fnmatch(string, match):
        return True
    return False
