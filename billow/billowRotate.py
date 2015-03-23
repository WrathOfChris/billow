from . import asg
import billow
import boto
from boto.exception import BotoServerError
from contextlib import closing
import itertools
import json
import sys
import time
import urllib2

class billowRotate(object):
    """
    Rotate instance within a billowService
    """

    def __init__(self, service, region='us-east-1'):
        if not isinstance(service, billow.billowService):
            raise TypeError

        self.service = service
        self.instances = list()
        self.priority = list()
        self.__logger = self.consolelogger
        self.private_secondary_failures = list()
        self.urltimeout = 60

    def consolelogger(self, msg):
        sys.stderr.write("billowRotate %s: %s\n" % (self.service.service, msg))
        sys.stderr.flush()

    def set_logger(self, logfunction):
        self.__logger = logfunction

    def log(self, msg):
        self.__logger(msg)

    def safety(self):
        """
        1. Check for no instances
        2. Check for redundancy reduction in each zone
        3. Check for (cur == max <= 1)
        4. Check CrossZoneLB disabled and empty AZ
        5. Check instances for secondary Private IPs and multi-subnet
        """
        warnings = list()
        for g in self.service.groups:
            instances = g.instances

            # 1. Check for no instances
            if len(instances) == 0:
                warnings.append("%s no instances to rotate" % g.group)

            # 2. Check for redundancy reduction in each zone
            zones = dict()
            for i in instances:
                if i.zone not in zones:
                    zones[ i.zone ] = 0
                zones[ i.zone ] += 1
            for k, v in zones.iteritems():
                if v <= 2:
                    warnings.append('%s reduced redundancy, single instance ' \
                            'will remain in zone %s' % (g.group, k))

            # 3. Check for (cur == max == 1)
            if g.cur_size == 1 and g.max_size == 1:
                warnings.append("%s temporary outage, single instance in ' \
                        'group" % g.group)

            # 4. Check CrossZoneLB disabled and empty AZ
            for b in self.service.balancers:
                if ('crosszone' in b.options and
                        b.options['crosszone'] == False):
                    for z in b.zones:
                        if z in zones and zones[z] <= 1:
                            warnings.append("%s deadend traffic, zoned ' \
                                    'balancer without cross-zone in %s" % \
                                    (g.group, z))

            # 5. Check instances for secondary Private IPs and multi-subnet
            for i in instances:
                for ni in i.interfaces:
                    if (len(g.subnets) > 1 and \
                            'private_ip_addresses' in ni and \
                            len(ni['private_ip_addresses']) > 0):
                        warnings.append('%s instance %s has secondary ' \
                                'private IP address %s but group has ' \
                                'multiple subnets' \
                                % (g.group, i.id,
                                    ni['private_ip_addresses'][0]))

        return warnings

    def roundrobin(self, *iterables):
        "roundrobin('ABC', 'D', 'EF') --> A D E B F C"
        # https://docs.python.org/2/library/itertools.html#recipes
        # Recipe credited to George Sakkis
        pending = len(iterables)
        nexts = itertools.cycle(iter(it).next for it in iterables)
        while pending:
            try:
                for next in nexts:
                    yield next()
            except StopIteration:
                pending -= 1
                nexts = itertools.cycle(itertools.islice(nexts, pending))

    def order(self):
        """
        1. UnHealthy Group instances
        2. Degraded Balancer instances
        3. All instances
        4. Round-robin interleave Groups
        """
        self.instances = list()
        degraded = list()
        instances = list()

        # 1. UnHealthy Group instances
        for g in self.service.groups:
            for i in g.instances:
                if i.group_health != 'Healthy' and i.id not in degraded:
                    degraded.append(i.id)

        # 2. Degraded Balancer instances
        for b in self.service.balancers:
            for i in b.instances:
                if i.balancer_state != 'InService' and i.id not in degraded:
                    degraded.append(i.id)

        # 3. All instances
        for g in self.service.groups:
            instlist = list()
            for i in g.instances:
                if i.id not in degraded and i.group_state == 'InService':
                    instlist.append(i.id)
            instances.append(instlist)

        # Build rotation order
        self.instances.extend(degraded)
        self.instances.extend(self.roundrobin(*instances))

        return self.instances

    def find_group_by_instance(self, instance_id):
        for g in self.service.groups:
            if instance_id in g.instances:
                return g
        return None

    def find_balancer(self, balancer_name):
        for b in self.service.balancers:
            if b.name == balancer_name:
                return b
        return None

    def find_balancer_instance(self, balancer, instance_id):
        for i in balancer.instances:
            if i.id == instance_id:
                return i
        return None

    def find_group_instance(self, group, instance_id):
        for i in group.instances:
            if i.id == instance_id:
                return i
        return None

    def wait_timeout(self, timeout, starttime):
        waittime = timeout - (time.time() - starttime)
        if waittime <= 0:
            self.log('timed out, aborting')
            return 0
        return waittime

    def wait_elb_registered(self, instance_id, sleep=5, timeout=None):
        """
        Wait for instance to become registered to balancer
        Registration means 'InService' or 'OutOfService'
        Ignore 'Unknown' and consider it unregistered in Unknown state
        """
        starttime = 0
        if timeout:
            if timeout < 0:
                self.log('timed out waiting for balancer registration')
                return False
            starttime = time.time()

        healthy = False
        while not healthy:
            group = self.find_group_by_instance(instance_id)
            if not group:
                self.log('no group found, cannot wait for instance %s ' \
                        'balancer registration' % instance_id)
                return False

            healthycnt = 0
            for balancer_name in group.load_balancers:
                balancer = self.find_balancer(balancer_name)
                if not balancer:
                    self.log('no balancer found, cannot wait for instance ' \
                            '%s registration to balancer %s' \
                            % (instance_id, balancer_name))
                    return False

                # Refresh ELB info
                balancer.refresh()

                instance = self.find_balancer_instance(balancer, instance_id)
                if not instance:
                    continue

                if instance.balancer_state == 'InService' or \
                        instance.balancer_state == 'OutOfService':
                    healthycnt += 1

            if healthycnt == len(group.load_balancers):
                return True

            if timeout and (time.time() - starttime) > timeout:
                self.log('timed out waiting for instance %s balancer ' \
                        'deregistration' % instance_id)
                return False

            if not healthy:
                timeoutstr = ''
                if timeout:
                    timeoutstr = ' timeout %ds' \
                            % int(timeout - (time.time() - starttime))
                self.log('sleeping %ds waiting for instance %s to register ' \
                        'with %d/%d balancers%s' % (
                            sleep,
                            instance_id,
                            healthycnt,
                            len(group.load_balancers),
                            timeoutstr)
                        )
                time.sleep(sleep)

        return True

    def wait_elb_deregistered(self, instance_id, sleep=5, timeout=None):
        """
        Wait for instance to deregister from balancer
        Consider 'Unknown' as deregistered
        """
        starttime = 0
        if timeout:
            if timeout < 0:
                self.log('timed out waiting for balancer deregistration')
                return False
            starttime = time.time()

        healthy = True
        while healthy:
            drainmax = 0

            group = self.find_group_by_instance(instance_id)
            if not group:
                self.log('no group found, cannot wait for instance %s ' \
                        'balancer deregistration' % instance_id)
                return False

            unhealthycnt = 0
            for balancer_name in group.load_balancers:
                balancer = self.find_balancer(balancer_name)
                if not balancer:
                    self.log('balancer not found, cannot wait for instance ' \
                            '%s deregistration from balancer %s' \
                            % (instance_id, balancer_name))
                    return False

                # Refresh ELB info
                balancer.refresh()

                instance = self.find_balancer_instance(balancer, instance_id)
                if not instance:
                    unhealthycnt += 1
                    continue

                if (balancer.connection_draining and \
                        instance.balancer_state == 'InService: Instance ' \
                        'deregistration currently in progress'):
                    drainmax = max(drainmax,
                            balancer.connection_draining_timeout)

                if (instance.balancer_state == 'OutOfService' or \
                        instance.balancer_state == 'OutOfService: Instance ' \
                            'is not currently registered with the '
                            'LoadBalancer' or \
                         instance.balancer_state == 'Unknown'):
                    unhealthycnt += 1
                    continue

            if unhealthycnt == len(group.load_balancers):
                return True

            if timeout and (time.time() - starttime) > timeout:
                self.log('timed out waiting for instance %s balancer ' \
                        'deregistration' % instance_id)
                return False

            if healthy:
                timeoutstr = ''
                if timeout:
                    timeoutstr = ' timeout %ds' \
                            % int(timeout - (time.time() - starttime))
                drainstr = ''
                if drainmax:
                    drainstr = ' draining connections %ds' % drainmax
                self.log('sleeping %ds waiting for instance %s to ' \
                        'deregister with %d/%d balancers%s%s' % (
                            sleep,
                            instance_id,
                            unhealthycnt,
                            len(group.load_balancers),
                            timeoutstr,
                            drainstr)
                        )
                time.sleep(sleep)

        return True

    def wait_elb_healthy(self, instance_id, sleep=5, timeout=None):
        starttime = time.time()
        if timeout:
            if timeout < 0:
                self.log('timed out waiting for balancer health check')
                return False

        healthchecks = dict()
        healthtimes = dict()
        healthy = False
        while not healthy:
            group = self.find_group_by_instance(instance_id)
            if not group:
                self.log('no group found, cannot wait for instance %s ' \
                        'balancer health check')
                return False

            healthycnt = 0
            healthchecks = dict()
            for balancer_name in group.load_balancers:
                balancer = self.find_balancer(balancer_name)
                if not balancer:
                    self.log('no balancer found, cannot wait for instance ' \
                            '%s health check to balancer %s' \
                            % (instance_id, balancer_name))
                    return False

                # Refresh ELB info
                balancer.refresh()

                instance = self.find_balancer_instance(balancer, instance_id)
                if not instance:
                    continue

                if instance.balancer_state == 'InService':
                    healthycnt += 1
                else:
                    healthchecks[balancer.name] = balancer.health_target
                    healthtimes[balancer.name] = \
                            balancer.health_timeout * balancer.health_threshold

            if healthycnt == len(group.load_balancers):
                return True

            if timeout and (time.time() - starttime) > timeout:
                self.log('timed out waiting for instance %s health check' \
                        % instance_id)
                return False

            if not healthy:
                timeoutstr = ''
                if timeout:
                    timeoutstr = ' timeout %ds' \
                            % int(timeout - (time.time() - starttime))
                self.log('sleeping %ds waiting for instance %s health check ' \
                        'with %d/%d balancers%s' % (
                            sleep,
                            instance_id,
                            healthycnt,
                            len(group.load_balancers),
                            timeoutstr)
                        )
                now = time.time()
                for balancer_name, target in healthchecks.iteritems():
                    if (now - starttime) > healthtimes[balancer_name]:
                        self.log('instance %s failing balancer %s health ' \
                                'check %s' \
                                % (instance_id, balancer_name, target))
                time.sleep(sleep)

        return True

    def wait_group_terminated(self, instance_id, sleep=5, timeout=None):
        """
        Wait for instance to terminate from group
        """
        starttime = 0
        if timeout:
            if timeout < 0:
                self.log('timed out waiting for instance group termination')
                return False
            starttime = time.time()

        healthy = True
        while healthy:
            group = self.find_group_by_instance(instance_id)
            if not group:
                self.log('no group found, cannot wait for instance %s ' \
                        'group termination' % instance_id)
                return False

            # Refresh Group info
            group.refresh()

            instance = self.find_group_instance(group, instance_id)
            if not instance:
                return True

            if instance.group_state == 'Terminated' or \
                    instance.instance_state == 'terminated':
                return True

            if timeout and (time.time() - starttime) > timeout:
                self.log('timed out waiting for instance %s termination ' \
                        'from group %s' % (instance_id, group.name))
                return False

            timeoutstr = ''
            if timeout:
                timeoutstr = ' timeout %ds' \
                        % int(timeout - (time.time() - starttime))
            self.log('sleeping %ds waiting for instance %s in state %s to ' \
                    'terminate from group %s%s' % (
                        sleep,
                        instance_id,
                        instance.group_state,
                        group.name,
                        timeoutstr)
                    )
            time.sleep(sleep)

        return True

    def wait_group_launched(self, group, instances,
            count=1, sleep=5, timeout=None):
        """
        Wait for new instance(s) to start
        """
        if not isinstance(instances, list):
            instances = [instances]

        starttime = 0
        if timeout:
            if timeout < 0:
                self.log('timed out waiting for instance group launch')
                return False
            starttime = time.time()

        healthy = False
        while not healthy:
            healthycnt = 0
            healthytext = None
            healthyinstances = list()

            # Refresh Group info
            group.refresh()

            # Look for new instances not in previous list
            for i in group.instances:
                if i.id not in instances:
                    # Warn when unexpectate state discovered
                    if (i.group_state == 'Terminated' or \
                            i.group_state == 'Terminating' or \
                            i.group_state == 'Standby' or \
                            i.group_state.startswith('Terminating:') or \
                            i.instance_state == 'shutting-down' or \
                            i.instance_state == 'terminated' or \
                            i.instance_state == 'stopping' or \
                            i.instance_state == 'stopped'):
                        self.log('degraded instance %s found in ' \
                                'group state %s instance state %s' \
                                % (i.id, i.group_state, i.instance_state))
                        continue

                    # Display Pending if any are pending
                    if i.group_state == 'Pending':
                        healthytext = i.group_state

                    # Only display InService if no Pending
                    if not healthytext and i.group_state == 'InService':
                        healthytext = i.group_state

                    if i.group_state == 'InService':
                        healthycnt += 1
                        healthyinstances.append(i.id)

            if healthycnt >= count:
                return healthyinstances

            if timeout and (time.time() - starttime) > timeout:
                self.log('timed out waiting for instance start ' \
                        'from group %s' % group.name)
                return False

            timeoutstr = ''
            if timeout:
                timeoutstr = ' timeout %ds' \
                        % int(timeout - (time.time() - starttime))
            statestr = ''
            if healthytext:
                statestr = ' in state %s' % healthytext
            self.log('sleeping %ds launched %d, waiting for %d instances%s ' \
                    'to start in group %s%s' % (
                        sleep,
                        healthycnt,
                        count,
                        statestr,
                        group.name,
                        timeoutstr)
                    )
            time.sleep(sleep)

        return list()

    def wait_launch(self, group, instlist, timeout=None):
        """
        Wait for a newly launched instance to come into service
        """
        if timeout and timeout < 0:
            self.log('timed out waiting for instance launch')
            return False

        # Wait for new instance to enter Group
        ret = self.wait_group_launched(group, instlist, timeout=timeout)
        if not ret:
            return False

        # Wait for all instances to register with Balancer
        for i in ret:
            if not self.wait_elb_registered(i, timeout=timeout):
                return False

        # Wait for all instances to pass health checks
        for i in ret:
            if not self.wait_elb_healthy(i, timeout=timeout):
                return False

        # list of instance_id
        return ret

    def launch(self, group, wait=True, timeout=None):
        """
        launch a new instance
        """
        # Capture current group list to detect new instance
        instlist = group.instances

        if not group.increment():
            self.log('group launch instance failed')
            return False

        if wait:
            if not self.wait_lauch(group, instlist, timeout=timeout):
                return False

        return True

    def deregister(self, instance_id, wait=True, timeout=None):
        ret = True
        for b in self.service.balancers:
            if instance_id not in b.instances:
                self.log('instance %s already deregistered from balancer %s' \
                        % (instance_id, b.name))
                continue
            if not b.deregister(instance_id):
                ret = False

        if wait:
            if not self.wait_elb_deregistered(instance_id, timeout=timeout):
                ret = False

        return ret

    def register(self, instance_id, wait=True, healthy=False, timeout=None):
        if timeout:
            starttime = time.time()

        ret = True
        group = self.find_group_by_instance(instance_id)
        if not group:
            self.log('no group found, cannot register instance %s to ' \
                    'balancer' % instance_id)
            return False

        for balancer_name in group.load_balancers:
            balancer = self.find_balancer(balancer_name)
            if not balancer:
                self.log('balancer %s not found, cannot wait for ' \
                        'balancer deregistration' % balancer_name)
                return False

            if not balancer.register(instance_id):
                ret = False

        if wait:
            waittime = timeout
            if timeout:
                waittime = self.wait_timeout(timeout, starttime)
            if not self.wait_elb_registered(instance_id, timeout=waittime):
                ret = False

            if healthy:
                if timeout:
                    waittime = self.wait_timeout(timeout, starttime)
                if not self.wait_elb_healthy(instance_id, timeout=waittime):
                    ret = False

        return ret

    def terminate(self, instance_id, decrement_capacity=False, wait=True,
            timeout=None):
        ret = True
        group = self.find_group_by_instance(instance_id)
        if not group:
            self.log('no group found, cannot terminate instance %s' \
                    % instance_id)
            return False

        try:
            if not group.terminate(
                    instance_id,
                    decrement_capacity=decrement_capacity
                    ):
                self.log('failed terminating instance %s from group %s' \
                        % (instance_id, group.name))
                return False
        except BotoServerError as e:
            if e.error_code == 'ValidationError':
                self.log('instance %s not managed, failed terminating from ' \
                        'group %s' % (instance_id, group.name))
                return False
            elif e.error_code == 'ScalingActivityInProgress':
                self.log('instance %s scaling activity in progress, failed ' \
                        'terminating from group %s' \
                        % (instance_id, group.name))
                return False
            else:
                raise e

        if wait:
            if not self.wait_group_terminated(instance_id, timeout=timeout):
                ret = False

        return ret

    def notify_terminate(self, group, instance_id, timeout=None):
        if 'urlterminate' not in group.settings:
            return True
        split = group.settings['urlterminate'].split(':')
        if len(split) != 2:
            self.log("instance %s terminate url invalid config")
            return False
        port = int(split[0])
        path = split[1]

        if port == 0 or path[0] != '/':
            self.log("instance %s terminate url invalid config")
            return False

        instance = self.find_group_instance(group, instance_id)
        if not instance:
            return False

        # Always require a timeout
        if not timeout:
            timeout = self.urltimeout

        url = 'http://%s:%d%s' % (instance.private_ip_address, port, path)
        data = '{}'
        header = {'Content-Type': 'application/json;charset=UTF-8'}
        req = urllib2.Request(url, data, header)

        self.log("instance %s terminate url %s" % (instance_id, url))
        try:
            with closing(urllib2.urlopen(req, timeout=timeout)) as f:
                response = json.loads(f.read())
        except ValueError:
            # Invalid JSON
            response = dict()
        except urllib2.URLError, e:
            self.log("instance %s terminate url failure %s" % \
                    (instance_id, e.reason))
            if str(e.reason) == "timed out":
                return False
            raise
        except urllib2.HTTPError, e:
            self.log("instance %s terminate url failure code %d" % \
                    (instance_id, e.code))
            raise

        return True

    def wait_notify(self, group, instance_id, sleep=5, timeout=None,
            hardfail_is_success=False):
        """
        Wait for GET to 'urlstatus' to return "OK" or '{"status": "OK"}'
        """
        if 'urlstatus' not in group.settings:
            return True
        split = group.settings['urlstatus'].split(':')
        if len(split) != 2:
            self.log("instance %s status url invalid config")
            return False
        port = int(split[0])
        path = split[1]

        if port == 0 or path[0] != '/':
            self.log("instance %s status url invalid config")
            return False

        # Always require a timeout
        urltimeout = timeout
        if not timeout:
            urltimeout = self.urltimeout

        starttime = 0
        if timeout:
            starttime = time.time()

        healthy = False
        while not healthy:
            instance = self.find_group_instance(group, instance_id)
            if not instance:
                self.log('no instance found, cannot wait for instance %s ' \
                        'url status' % instance_id)
                return False

            url = 'http://%s:%d%s' % (instance.private_ip_address, port, path)
            data = '{}'
            header = {'Content-Type': 'application/json;charset=UTF-8'}
            req = urllib2.Request(url, data, header)

            healthy = True
            try:
                with closing(urllib2.urlopen(req, timeout=urltimeout)) as f:
                    raw = f.read()
                    response = json.loads(raw)
            except ValueError, e:
                # Invalid JSON
                response = dict()
                if isinstance(raw, str):
                    response['status'] = raw
            except urllib2.URLError, e:
                self.log("instance %s status url failure %s" % \
                        (instance_id, e.reason))
                healthy = False
                if str(e.reason) != "timed out":
                    if not hardfail_is_success:
                        raise
                    else:
                        # hardfail is sometimes success
                        healthy = True
            except urllib2.HTTPError, e:
                self.log("instance %s status url failure code %d" % \
                        (instance_id, e.code))
                if not hardfail_is_success:
                    raise

            if 'status' in response:
                if response['status'] != 'OK':
                    healthy = False

            if not healthy and timeout and (time.time() - starttime) > timeout:
                self.log('timed out waiting for instance %s status url' \
                        % instance_id)
                return False

            if not healthy:
                timeoutstr = ''
                if timeout:
                    timeoutstr = ' timeout %ds' \
                            % int(timeout - (time.time() - starttime))
                self.log('sleeping %ds waiting for instance %s status url ' \
                        '%s%s' % (sleep, instance_id, url, timeoutstr))
                time.sleep(sleep)

        return True

    def rotate_instance(self, instance_id, wait=True, timeout=None):
        """
        Rotate a single instance in a Group
        """
        terminate_after = True
        if timeout:
            starttime = time.time()

        group = self.find_group_by_instance(instance_id)
        if not group:
            self.log('no group found, cannot rotate instance %s' \
                    % instance_id)
            return False

        if 'rotate' in group.settings and group.settings['rotate'] == False:
            self.log('skipping rotation of instance %s due to tag ' \
                    'rotate=false' % instance_id)
            return True

        # Capture current group list to detect new instance
        instlist = group.instances

        #
        # URL NOTIFY - HTTP request to instance endpoint for termination
        #
        if not self.notify_terminate(group, instance_id, timeout=timeout):
            return False
        if not self.wait_notify(group, instance_id, timeout=timeout):
            return False

        elasticips = self.get_elasticips(instance_id)
        for e in elasticips:
            self.log('disassociating static IP %s association %s ' \
                    'allocation %s interface %s' \
                    % (e['public_ip_address'], e['association_id'],
                        e['allocation_id'], e['network_interface_id']))
            group.asg.disassociate_address(e['association_id'])

        privateips = self.get_secondaryips(instance_id)
        for p in privateips:
            self.log('unassigning private IP %s interface %s' \
                    % (p['private_ip_address'], p['network_interface_id']))
            group.asg.unassign_private_ip_addresses(
                    network_interface_id=p['network_interface_id'],
                    private_ip_addresses=p['private_ip_address']
                    )

        # Terminate before launch
        if group.cur_size == group.max_size:
            terminate_after = False

            self.log('terminating instance %s' % instance_id)

            # Do not wait for termination, instead wait for launched instance
            if not self.terminate(instance_id, wait=False):
                return False

        # Increase Group size
        else:
            self.log('launching instance')

            if not group.increment():
                self.log('group launch instance failed')
                return False

        # Wait for new instance to enter Group
        ret = self.wait_group_launched(group, instlist, timeout=timeout)
        if not ret:
            return False
        if len(ret) > 1:
            self.log('expected 1 instance launch, found %d' % len(ret))

        # Put back Elastic / Private IPs
        newinstance = ret[0]
        for e in elasticips:
            self.log('associating static IP %s allocation %s' \
                    % (e['public_ip_address'], e['allocation_id']))
            ret = self.put_elasticip(newinstance, e['allocation_id'])
            if not ret:
                self.log('failed associating static IP %s allocation %s' \
                        % (e['public_ip_address'], e['allocation_id']))
                return False

        for p in privateips:
            self.log('assigning private IP %s' % p['private_ip_address'])
            ret = self.put_secondaryip(newinstance, p['private_ip_address'])
            if not ret:
                self.private_secondary_failures.append(p['private_ip_address'])

        # Full launch wait after addresses associated
        waittime = timeout
        if timeout:
            waittime = self.wait_timeout(timeout, starttime)
        ret = self.wait_launch(group, instlist, timeout=waittime)
        if ret == False:
            return False

        if terminate_after:
            if timeout:
                waittime = self.wait_timeout(timeout, starttime)

            self.log('terminating instance %s' % instance_id)

            # Terminate and wait
            if not self.terminate(instance_id, decrement_capacity=True,
                    wait=True, timeout=waittime):
                return False

        return True

    def rotate(self, wait=True, timeout=None):
        if timeout:
            starttime = time.time()

        errors = 0

        rotatelist = self.order()
        for instance in rotatelist:
            waittime = timeout
            if timeout:
                waittime = self.wait_timeout(timeout, starttime)
                # Abort rotation if no time left on the clock
                if waittime <= 0:
                    return False
            ret = self.rotate_instance(instance, timeout=timeout)
            if not ret:
                self.log('failed rotating %s' % instance)
                errors += 1
                continue

        # Post-rotation attempt to associate orphaned private IPs
        if self.private_secondary_failures:
            self.finalize_secondaryip()
            errors += len(self.private_secondary_failures)

        if errors > 0:
            self.log('finished: %d FAILURES' % errors)
            return False

        self.log('finished: success')
        return True

    def get_elasticips(self, instance_id):
        elasticips = list()

        group = self.find_group_by_instance(instance_id)
        if not group:
            return list()

        instance = self.find_group_instance(group, instance_id)
        if not instance:
            return list()

        addrlist = list()
        for n in instance.interfaces:
            # ElasticIPs are owned by account number, standard by 'amazon'
            if 'owner' in n and n['owner'] != 'amazon':
                addrlist.append(n['public_ip_address'])

        if not addrlist:
            return list()

        addrs = group.asg.get_addresses(addrlist)
        for a in addrs:
            addr = {
                    'public_ip_address': a.public_ip,
                    'private_ip_address': a.private_ip_address,
                    'instance_id': a.instance_id,
                    'allocation_id': a.allocation_id,
                    'association_id': a.association_id,
                    'network_interface_id': a.network_interface_id
                    }
            elasticips.append(addr)

        return elasticips

    def put_elasticip(self, instance_id, allocation_id):
        group = self.find_group_by_instance(instance_id)
        if not group:
            return False

        instance = self.find_group_instance(group, instance_id)
        if not instance:
            return False

        if not instance.interfaces:
            return False

        ret = group.asg.associate_address(
                allocation_id,
                instance_id=instance_id,
                network_interface_id=instance.interfaces[0]['id'])

        return ret

    def get_secondaryips(self, instance_id):
        group = self.find_group_by_instance(instance_id)
        if not group:
            return list()

        instance = self.find_group_instance(group, instance_id)
        if not instance:
            return list()

        addrlist = list()
        for n in instance.interfaces:
            if 'private_ip_addresses' in n:
                for a in n['private_ip_addresses']:
                    if a != n['private_ip_address']:
                        addr = {
                                'private_ip_address': a,
                                'instance_id': instance.id,
                                'network_interface_id': n['id']
                                }
                        addrlist.append(addr)

        return addrlist

    def put_secondaryip(self, instance_id, private_ip_address):
        if not private_ip_address:
            return False
        if not isinstance(private_ip_address, list):
            private_ip_address = [private_ip_address]

        group = self.find_group_by_instance(instance_id)
        if not group:
            return False

        instance = self.find_group_instance(group, instance_id)
        if not instance:
            return False

        if not instance.interfaces:
            return False

        try:
            ret = group.asg.assign_private_ip_addresses(
                    network_interface_id=instance.interfaces[0]['id'],
                    private_ip_addresses=private_ip_address
                    )
        except BotoServerError as e:
            if e.error_code == 'InvalidParameterValue':
                self.log('failed assigning secondary private IP %s to ' \
                        'instance %s interface %s' \
                        % (private_ip_address[0], instance_id,
                            instance.interfaces[0]['id']))
                return False
            else:
                raise e

        return ret

    def finalize_secondaryip(self):
        for g in self.service.groups:
            for i in g.instances:
                if not self.private_secondary_failures:
                    return
                for ni in i.interfaces:
                    if ('private_ip_addresses' not in ni or \
                            len(ni['private_ip_addresses']) == 0):
                        for p in self.private_secondary_failures:
                            ret = self.put_secondaryip(i.id, p)
                            if ret:
                                self.log('repair assigned private IP %s ' \
                                        'to instance %s' % (p, i.id))
                                self.private_secondary_failures.remove(p)
                                break

        for p in self.private_secondary_failures:
            self.log('failed repairing assignment of private IP %s' % p)
