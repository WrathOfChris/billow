import argparse
import sys
import errno
import json
import yaml
import pprint
from .util import common_parser, common_args, catch_sigint
import billow
import re


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
        '--info',
        help='full info',
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
        if args.info:
            output.append(s.info())
        else:
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

            for k, v in o.iteritems():
                if isinstance(v, str):
                    print "%s: %s" % (k, str(v))
                else:
                    print "%s: %s" % (k, pprint.pformat(v))

    sys.exit(0)


def billow_find_images():
    catch_sigint()
    parser = common_parser('billow find images')
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
        'image',
        type=str,
        help='image to find'
    )
    args = parser.parse_args()
    common_args(args)

    if '-' not in args.image:
        sys.stderr.write('service-environ required\n')
        sys.exit(1)

    service = args.image.rsplit('-')[0]
    environ = args.image.rsplit('-')[1]

    output = list()
    bc = billow.billowCloud(regions=args.regions)
    for r in bc.regions:
        i = billow.billowImage(region=r.region, parent=r)
        images = i.list_dated_newest(service, environ)
        for image in images:
            output.append({
                'id': image.id,
                'name': image.name,
                'description': image.description
            })

    if args.json:
        print json.dumps(output, indent=4, separators=(',', ': '))
    elif args.yaml:
        print yaml.safe_dump(output, encoding='utf-8', allow_unicode=True)
    else:
        for o in output:
            print "%s %s" % (str(o['id']), str(o['name']))

    sys.exit(0)


def billow_list_images():
    catch_sigint()
    parser = common_parser('billow list images')
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
    parsergroup.add_argument(
        '--regex',
        help='regex filter',
        type=str
    )
    parser.add_argument(
        'image',
        type=str,
        help='image to find'
    )
    args = parser.parse_args()
    common_args(args)

    output = list()
    bc = billow.billowCloud(regions=args.regions)
    for r in bc.regions:
        i = billow.billowImage(region=r.region, parent=r)
        try:
            images = i.search(args.image, regex=args.regex)
        except re.error:
            sys.stderr.write('bad regex\n')
            sys.exit(errno.EINVAL)
        for image in images:
            output.append({
                'id': image.id,
                'name': image.name,
                'description': image.description
            })

    if args.json:
        print json.dumps(output, indent=4, separators=(',', ': '))
    elif args.yaml:
        print yaml.safe_dump(output, encoding='utf-8', allow_unicode=True)
    else:
        for o in output:
            print "%s %s" % (str(o['id']), str(o['name']))

    sys.exit(0)


def billow_find_configs():
    catch_sigint()
    parser = common_parser('billow find configs')
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
        'config',
        type=str,
        help='config to find'
    )
    args = parser.parse_args()
    common_args(args)

    if '-' not in args.config:
        sys.stderr.write('service-environ required\n')
        sys.exit(1)

    service = args.config.rsplit('-')[0]
    environ = args.config.rsplit('-')[1]

    output = list()
    bc = billow.billowCloud(regions=args.regions)
    for r in bc.regions:
        c = billow.billowConfig(region=r.region, parent=r)
        configs = c.list_dated_newest(service, environ)
        for config in configs:
            output.append({
                'name': config.name,
                'image_id': config.image_id
            })

    if args.json:
        print json.dumps(output, indent=4, separators=(',', ': '))
    elif args.yaml:
        print yaml.safe_dump(output, encoding='utf-8', allow_unicode=True)
    else:
        for o in output:
            print "%s %s" % (str(o['name']), str(o['image_id']))

    sys.exit(0)


def billow_list_configs():
    catch_sigint()
    parser = common_parser('billow list configs')
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
        'config',
        type=str,
        help='config to find'
    )
    args = parser.parse_args()
    common_args(args)

    output = list()
    bc = billow.billowCloud(regions=args.regions)
    for r in bc.regions:
        c = billow.billowConfig(region=r.region, parent=r)
        configs = c.match(args.config)
        for config in configs:
            output.append({
                'name': config.name,
                'image_id': config.image_id
            })

    if args.json:
        print json.dumps(output, indent=4, separators=(',', ': '))
    elif args.yaml:
        print yaml.safe_dump(output, encoding='utf-8', allow_unicode=True)
    else:
        for o in output:
            print "%s %s" % (str(o['name']), str(o['image_id']))

    sys.exit(0)


def billow_list_rotate():
    catch_sigint()
    parser = common_parser('billow list rotate')
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
        'service',
        type=str,
        help='service to rotate'
    )
    args = parser.parse_args()
    common_args(args)

    output = list()
    bc = billow.billowCloud(regions=args.regions)
    services = bc.get_service(args.service)
    if not services:
        sys.stderr.write('no service found\n')
        sys.exit(errno.ENOENT)
    for s in services:
        r = billow.billowRotate(s)
        warnings = r.safety()
        for w in warnings:
            sys.stderr.write('WARNING: %s\n' % w)

        for i in r.order():
            output.append(i)

    if args.json:
        print json.dumps(output, indent=4, separators=(',', ': '))
    elif args.yaml:
        print yaml.safe_dump(output, encoding='utf-8', allow_unicode=True)
    else:
        for o in output:
            print str(o)

    sys.exit(0)


def billow_rotate():
    catch_sigint()
    parser = common_parser('billow rotate')
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
        'service',
        type=str,
        help='service to rotate'
    )
    args = parser.parse_args()
    common_args(args)

    output = list()
    bc = billow.billowCloud(regions=args.regions)
    services = bc.get_service(args.service)
    if not services:
        sys.stderr.write('no service found\n')
        sys.exit(errno.ENOENT)
    for s in services:
        r = billow.billowRotate(s)
        warnings = r.safety()
        for w in warnings:
            sys.stderr.write('WARNING: %s\n' % w)

        ret = r.rotate(timeout=60)
        if not ret:
            output.append("FAILED")

    if args.json:
        print json.dumps(output, indent=4, separators=(',', ': '))
    elif args.yaml:
        print yaml.safe_dump(output, encoding='utf-8', allow_unicode=True)
    else:
        for o in output:
            print str(o)

    sys.exit(0)


def billow_rotate_deregister():
    catch_sigint()
    parser = common_parser('billow rotate deregister')
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
    parsergroup.add_argument(
        '--nowait',
        help='do not wait for deregistration',
        action='store_true'
    )
    parser.add_argument(
        '--service',
        type=str,
        help='service'
    )
    parser.add_argument(
        'instance',
        type=str,
        help='instance to deregister'
    )
    args = parser.parse_args()
    common_args(args)
    wait = True
    if args.nowait:
        wait = False

    output = list()
    bc = billow.billowCloud(regions=args.regions)
    services = bc.get_service(args.service)
    if not services:
        sys.stderr.write('no service found\n')
        sys.exit(errno.ENOENT)
    for s in services:
        r = billow.billowRotate(s)

        r.deregister(args.instance, wait=wait)

    if args.json:
        print json.dumps(output, indent=4, separators=(',', ': '))
    elif args.yaml:
        print yaml.safe_dump(output, encoding='utf-8', allow_unicode=True)
    else:
        for o in output:
            print str(o)

    sys.exit(0)


def billow_rotate_register():
    catch_sigint()
    parser = common_parser('billow rotate deregister')
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
    parsergroup.add_argument(
        '--nowait',
        help='do not wait for deregistration',
        action='store_true'
    )
    parser.add_argument(
        '--service',
        type=str,
        help='service'
    )
    parser.add_argument(
        'instance',
        type=str,
        help='instance to register'
    )
    args = parser.parse_args()
    common_args(args)
    wait = True
    if args.nowait:
        wait = False

    output = list()
    bc = billow.billowCloud(regions=args.regions)
    services = bc.get_service(args.service)
    if not services:
        sys.stderr.write('no service found\n')
        sys.exit(errno.ENOENT)
    for s in services:
        r = billow.billowRotate(s)

        r.register(args.instance, wait=wait, healthy=True)

    if args.json:
        print json.dumps(output, indent=4, separators=(',', ': '))
    elif args.yaml:
        print yaml.safe_dump(output, encoding='utf-8', allow_unicode=True)
    else:
        for o in output:
            print str(o)

    sys.exit(0)


def billow_rotate_terminate():
    catch_sigint()
    parser = common_parser('billow rotate terminate')
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
    parsergroup.add_argument(
        '--nowait',
        help='do not wait for termination',
        action='store_true'
    )
    parser.add_argument(
        '--service',
        type=str,
        help='service'
    )
    parser.add_argument(
        'instance',
        type=str,
        help='instance to terminate'
    )
    args = parser.parse_args()
    common_args(args)
    wait = True
    if args.nowait:
        wait = False

    output = list()
    bc = billow.billowCloud(regions=args.regions)
    services = bc.get_service(args.service)
    if not services:
        sys.stderr.write('no service found\n')
        sys.exit(errno.ENOENT)
    for s in services:
        r = billow.billowRotate(s)

        r.terminate(args.instance, wait=wait)

    if args.json:
        print json.dumps(output, indent=4, separators=(',', ': '))
    elif args.yaml:
        print yaml.safe_dump(output, encoding='utf-8', allow_unicode=True)
    else:
        for o in output:
            print str(o)

    sys.exit(0)


def billow_rotate_instance():
    catch_sigint()
    parser = common_parser('billow rotate instance')
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
    parsergroup.add_argument(
        '--nowait',
        help='do not wait for termination',
        action='store_true'
    )
    parser.add_argument(
        '--service',
        type=str,
        help='service'
    )
    parser.add_argument(
        'instance',
        type=str,
        help='instance to rotate'
    )
    args = parser.parse_args()
    common_args(args)
    wait = True
    if args.nowait:
        wait = False

    output = list()
    bc = billow.billowCloud(regions=args.regions)
    services = bc.get_service(args.service)
    if not services:
        sys.stderr.write('no service found\n')
        sys.exit(errno.ENOENT)
    for s in services:
        r = billow.billowRotate(s)
        r.rotate_instance(args.instance, wait=wait)

    if args.json:
        print json.dumps(output, indent=4, separators=(',', ': '))
    elif args.yaml:
        print yaml.safe_dump(output, encoding='utf-8', allow_unicode=True)
    else:
        for o in output:
            print str(o)

    sys.exit(0)
