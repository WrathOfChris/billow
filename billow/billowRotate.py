from . import asg
import billow
import boto
from boto.exception import BotoServerError
import itertools
import sys
import time

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
        """
        warnings = list()
        for g in self.service.groups:
            instances = g.instancestatus

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
        if timeout:
            if timeout < 0:
                self.log('timed out waiting for balancer health check')
                return False
            starttime = time.time()

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

        return True

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

        # Capture current group list to detect new instance
        instlist = group.instances

        # Terminate before launch
        if group.cur_size == group.max_size:
            terminate_after = False

            # Do not wait for termination, instead wait for launched instance
            if not self.terminate(instance_id, wait=False):
                return False

        # Increase Group size
        else:
            if not group.increment():
                self.log('group launch instance failed')
                return False

        waittime = timeout
        if timeout:
            waittime = self.wait_timeout(timeout, starttime)
        if not self.wait_launch(group, instlist, timeout=waittime):
            return False

        if terminate_after:
            if timeout:
                waittime = self.wait_timeout(timeout, starttime)
            # Terminate and wait
            if not self.terminate(instance_id, decrement_capacity=True,
                    wait=True, timeout=waittime):
                return False

        return True

    def rotate(self, wait=True, timeout=None):
        if timeout:
            starttime = time.time()

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
                continue

        return True

# TODO:
# - Rotation:
#   - Instance Persistence:
#     - ElasticIP disassociate
#     - ? ENI disassociate
#     - Secondary Private IP unassign
#     - ? EBS unmount
#   - Instance Persistence:
#     - ElasticIP associate
#     - Secondary IP associate