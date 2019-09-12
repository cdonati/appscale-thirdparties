def GenerateConfig(context):
    network_name = context.env['deployment']
    config_name = context.env['deployment']
    resources = [{
        'name': context.env['deployment'],
        'type': 'network-template.py'
    }, {
        'name': context.env['deployment'] + '-ssh',
        'type': 'firewall-template.py',
        'properties': {
            'network': network_name,
            'sourceRanges': ['0.0.0.0/0'],
            'allowed': [{
                'IPProtocol': 'TCP',
                'ports': [22]
            }]
        }
    }, {
        'name': context.env['deployment'] + '-internal',
        'type': 'firewall-template.py',
        'properties': {
            'network': network_name,
            'sourceRanges': ['10.128.0.0/20'],
            'allowed': [{
                'IPProtocol': 'tcp',
                'ports': ['0-65535']
            }, {
                'IPProtocol': 'udp',
                'ports': ['0-65535'],
            }, {
                'IPProtocol': 'icmp'
            }]
        }
    }, {
        'name': '{}-config'.format(context.env['deployment']),
        'type': 'runtimeconfig.v1beta1.config',
        'properties': {'config': config_name}
    }]

    init_order = ['{}-{}'.format(context.env['deployment'], index + 1)
                  for index in range(context.properties['vmCount'])]
    for vm_name in init_order:
        resources.append({
            'name': vm_name,
            'type': 'vm-template.py',
            'properties': {
                'machineType': 'f1-micro',
                'zone': 'us-central1-f',
                'network': network_name,
                'initOrder': init_order,
                'serviceAccount': context.properties['serviceAccount'],
                'configName': config_name
            }
        })

    return {'resources': resources}
