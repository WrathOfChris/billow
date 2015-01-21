import argparse
import sys
import json
import yaml
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
