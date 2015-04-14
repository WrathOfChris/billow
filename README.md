# billow
a large undulating mass of cloud services

# Command Line Tools

## billow-list

List all services

```
usage: billow-list [-h] [-a] [-r REGION] [--regions [REGIONS [REGIONS ...]]]
                   [-j | -y]

billow list

optional arguments:
  -h, --help            show this help message and exit
  -a, --auto            auto-detect (default: False)
  -r REGION, --region REGION
                        ec2 region (default: None)
  --regions [REGIONS [REGIONS ...]]
                        ec2 regions (default: None)
  -j, --json            json output (default: False)
  -y, --yaml            yaml output (default: False)
```

## billow-get

Get service configuration.

This is currently a mock of a future config grammar.

```
usage: billow-get [-h] [-a] [-r REGION] [--regions [REGIONS [REGIONS ...]]]
                  [-j | -y] [--info]
                  SERVICE [SERVICE ...]

billow get

positional arguments:
  SERVICE               list of services to get

optional arguments:
  -h, --help            show this help message and exit
  -a, --auto            auto-detect (default: False)
  -r REGION, --region REGION
                        ec2 region (default: None)
  --regions [REGIONS [REGIONS ...]]
                        ec2 regions (default: None)
  -j, --json            json output (default: False)
  -y, --yaml            yaml output (default: False)
  --info                full info (default: False)
```

## Launch Configurations

### billow-find-configs

Find Launch Configurations for a service, ordered from newest

```
usage: billow-find-configs [-h] [-a] [-r REGION]
                           [--regions [REGIONS [REGIONS ...]]] [-j | -y]
                           config

billow find configs

positional arguments:
  config                config to find

optional arguments:
  -h, --help            show this help message and exit
  -a, --auto            auto-detect (default: False)
  -r REGION, --region REGION
                        ec2 region (default: None)
  --regions [REGIONS [REGIONS ...]]
                        ec2 regions (default: None)
  -j, --json            json output (default: False)
  -y, --yaml            yaml output (default: False)
```

### billow-list-configs

List Launch Configurations based on a match string

```
usage: billow-list-configs [-h] [-a] [-r REGION]
                           [--regions [REGIONS [REGIONS ...]]] [-j | -y]
                           config

billow list configs

positional arguments:
  config                config to find

optional arguments:
  -h, --help            show this help message and exit
  -a, --auto            auto-detect (default: False)
  -r REGION, --region REGION
                        ec2 region (default: None)
  --regions [REGIONS [REGIONS ...]]
                        ec2 regions (default: None)
  -j, --json            json output (default: False)
  -y, --yaml            yaml output (default: False)
```

## Images

### billow-find-images

Find instance images, newest first

```
usage: billow-find-images [-h] [-a] [-r REGION]
                          [--regions [REGIONS [REGIONS ...]]] [-j | -y]
                          image

billow find images

positional arguments:
  image                 image to find

optional arguments:
  -h, --help            show this help message and exit
  -a, --auto            auto-detect (default: False)
  -r REGION, --region REGION
                        ec2 region (default: None)
  --regions [REGIONS [REGIONS ...]]
                        ec2 regions (default: None)
  -j, --json            json output (default: False)
  -y, --yaml            yaml output (default: False)
```

### billow-list-images

List instance images by regex

```
usage: billow-list-images [-h] [-a] [-r REGION]
                          [--regions [REGIONS [REGIONS ...]]]
                          [-j | -y | --regex REGEX]
                          image

billow list images

positional arguments:
  image                 image to find

optional arguments:
  -h, --help            show this help message and exit
  -a, --auto            auto-detect (default: False)
  -r REGION, --region REGION
                        ec2 region (default: None)
  --regions [REGIONS [REGIONS ...]]
                        ec2 regions (default: None)
  -j, --json            json output (default: False)
  -y, --yaml            yaml output (default: False)
  --regex REGEX         regex filter (default: None)
```

## Instance Rotation

### billow-rotate

Rotate the instances of a service.

```
usage: billow-rotate [-h] [-a] [-r REGION] [--regions [REGIONS [REGIONS ...]]]
                     [-j | -y] [--nowait | --timeout TIMEOUT]
                     service

billow rotate

positional arguments:
  service               service to rotate

optional arguments:
  -h, --help            show this help message and exit
  -a, --auto            auto-detect (default: False)
  -r REGION, --region REGION
                        ec2 region (default: None)
  --regions [REGIONS [REGIONS ...]]
                        ec2 regions (default: None)
  -j, --json            json output (default: False)
  -y, --yaml            yaml output (default: False)
  --nowait              do not wait for termination (default: False)
  --timeout TIMEOUT     action timeout in seconds (default: None)
```

### billow-rotate-info

Show rotation configuration present in the service tags

```
usage: billow-rotate-info [-h] [-a] [-r REGION]
                          [--regions [REGIONS [REGIONS ...]]] [-j | -y]
                          service

billow rotate

positional arguments:
  service               service to rotate

optional arguments:
  -h, --help            show this help message and exit
  -a, --auto            auto-detect (default: False)
  -r REGION, --region REGION
                        ec2 region (default: None)
  --regions [REGIONS [REGIONS ...]]
                        ec2 regions (default: None)
  -j, --json            json output (default: False)
  -y, --yaml            yaml output (default: False)
```

### billow-rotate-deregister

Deregister an instance from its load balancer

```
usage: billow-rotate-deregister [-h] [-a] [-r REGION]
                                [--regions [REGIONS [REGIONS ...]]] [-j | -y]
                                [--nowait | --timeout TIMEOUT]
                                [--service SERVICE]
                                instance

billow rotate deregister

positional arguments:
  instance              instance to deregister

optional arguments:
  -h, --help            show this help message and exit
  -a, --auto            auto-detect (default: False)
  -r REGION, --region REGION
                        ec2 region (default: None)
  --regions [REGIONS [REGIONS ...]]
                        ec2 regions (default: None)
  -j, --json            json output (default: False)
  -y, --yaml            yaml output (default: False)
  --nowait              do not wait for termination (default: False)
  --timeout TIMEOUT     action timeout in seconds (default: None)
  --service SERVICE     service (default: None)
```

### billow-rotate-instance

Rotate a single instance in a service

```
usage: billow-rotate-instance [-h] [-a] [-r REGION]
                              [--regions [REGIONS [REGIONS ...]]] [-j | -y]
                              [--nowait | --timeout TIMEOUT]
                              [--service SERVICE]
                              instance

billow rotate instance

positional arguments:
  instance              instance to rotate

optional arguments:
  -h, --help            show this help message and exit
  -a, --auto            auto-detect (default: False)
  -r REGION, --region REGION
                        ec2 region (default: None)
  --regions [REGIONS [REGIONS ...]]
                        ec2 regions (default: None)
  -j, --json            json output (default: False)
  -y, --yaml            yaml output (default: False)
  --nowait              do not wait for termination (default: False)
  --timeout TIMEOUT     action timeout in seconds (default: None)
  --service SERVICE     service (default: None)
```

### billow-rotate-register

Register an instance with the service's load balancers

```
usage: billow-rotate-register [-h] [-a] [-r REGION]
                              [--regions [REGIONS [REGIONS ...]]] [-j | -y]
                              [--nowait | --timeout TIMEOUT]
                              [--service SERVICE]
                              instance

billow rotate deregister

positional arguments:
  instance              instance to register

optional arguments:
  -h, --help            show this help message and exit
  -a, --auto            auto-detect (default: False)
  -r REGION, --region REGION
                        ec2 region (default: None)
  --regions [REGIONS [REGIONS ...]]
                        ec2 regions (default: None)
  -j, --json            json output (default: False)
  -y, --yaml            yaml output (default: False)
  --nowait              do not wait for termination (default: False)
  --timeout TIMEOUT     action timeout in seconds (default: None)
  --service SERVICE     service (default: None)
```

### billow-rotate-status

Show service status (if available)

```
usage: billow-rotate-status [-h] [-a] [-r REGION]
                            [--regions [REGIONS [REGIONS ...]]] [-j | -y]
                            service

billow rotate

positional arguments:
  service               service to rotate

optional arguments:
  -h, --help            show this help message and exit
  -a, --auto            auto-detect (default: False)
  -r REGION, --region REGION
                        ec2 region (default: None)
  --regions [REGIONS [REGIONS ...]]
                        ec2 regions (default: None)
  -j, --json            json output (default: False)
  -y, --yaml            yaml output (default: False)
```

### billow-rotate-terminate

Terminate an instance in a service

```
usage: billow-rotate-terminate [-h] [-a] [-r REGION]
                               [--regions [REGIONS [REGIONS ...]]] [-j | -y]
                               [--nowait | --timeout TIMEOUT]
                               [--service SERVICE]
                               instance [instance ...]

billow rotate terminate

positional arguments:
  instance              instances to terminate

optional arguments:
  -h, --help            show this help message and exit
  -a, --auto            auto-detect (default: False)
  -r REGION, --region REGION
                        ec2 region (default: None)
  --regions [REGIONS [REGIONS ...]]
                        ec2 regions (default: None)
  -j, --json            json output (default: False)
  -y, --yaml            yaml output (default: False)
  --nowait              do not wait for termination (default: False)
  --timeout TIMEOUT     action timeout in seconds (default: None)
  --service SERVICE     service (default: None)
```
