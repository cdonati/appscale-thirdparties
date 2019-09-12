def GenerateConfig(context):
    resources = [{
        'name': context.env['name'],
        'type': 'compute.v1.firewall',
        'properties': {
            'network': '$(ref.' + context.properties['network'] + '.selfLink)',
            'sourceRanges': context.properties['sourceRanges'],
            'allowed': context.properties['allowed']
        }
    }]
    return {'resources': resources}
