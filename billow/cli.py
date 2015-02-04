import argparse
import sys
import errno
import json
import yaml
import pprint
from .util import common_parser, common_args, catch_sigint
import billow


def billow_list():
    catch_sigint()
    parser = common_parser('billow list')
    parsergroup = parser.add_mutually_exclusive_group()
    parsergroup.add_argument(
        '-j',
        '--json',
        help='json output',
        action='store_true'
    )
    parsergroup.add_argument(
        '-y',
        '--yaml',
        help='yaml output',
        action='store_true'
    )
    args = parser.parse_args()
    common_args(args)

    output = list()
    bc = billow.billowCloud(regions=args.regions)
    services = bc.list_services()
    for s in services:
        output.append(str(s))

    if args.json:
        print json.dumps(output)
    elif args.yaml:
        print yaml.safe_dump(output, encoding='utf-8', allow_unicode=True)
    else:
        for o in output:
            print o

    sys.exit(0)


def billow_get():
    catch_sigint()
    parser = common_parser('billow get')
    parsergroup = parser.add_mutually_exclusive_group()
    parsergroup.add_argument(
        '-j',
        '--json',
        help='json output',
        action='store_true'
    )
    parsergroup.add_argument(
        '-y',
        '--yaml',
        help='yaml output',
        action='store_true'
    )
    parser.add_argument(
        'services',
        metavar='SERVICE',
        nargs='+',
        type=str,
        help='list of services to get'
    )
    args = parser.parse_args()
    common_args(args)

    output = list()
    bc = billow.billowCloud(regions=args.regions)
    services = bc.get_service(args.services)
    if not services:
        sys.stderr.write('no service found\n')
        sys.exit(errno.ENOENT)
    for s in services:
        output.append(s.config())

    if args.json:
        print json.dumps(output, indent=4, separators=(',', ': '))
    elif args.yaml:
        print yaml.safe_dump(output, encoding='utf-8', allow_unicode=True)
    else:
        _first = True
        for o in output:
            if not _first:
                print ""
            else:
                _first = False

            for k,v in o.iteritems():
                if isinstance(v, str):
                    print "%s: %s" % (k, str(v))
                else:
                    print "%s: %s" % (k, pprint.pformat(v))

    sys.exit(0)
