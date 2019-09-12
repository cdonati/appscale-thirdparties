COMPUTE_URL_BASE = 'https://www.googleapis.com/compute/v1'

S3_BUCKET = "https://appscale-build.s3.amazonaws.com"
CLIENTS = "foundationdb-clients_6.1.8-1_amd64.deb"
SERVER = "foundationdb-server_6.1.8-1_amd64.deb"

# This won't be needed for custom images.
INSTALL_PACKAGES = """
wget "{s3_bucket}/{clients}"
wget "{s3_bucket}/{server}"
apt-get install -y python
dpkg -i "{clients}" "{server}"
# Work around a bug in the package that starts the processes outside of systemd.
systemctl start foundationdb
systemctl stop foundationdb
""".format(s3_bucket=S3_BUCKET, clients=CLIENTS, server=SERVER)

LEADER_TEMPLATE = """
#!/bin/bash
{install_packages}
systemctl start foundationdb
/usr/lib/foundationdb/make_public.py -a "$(hostname -I | xargs)"
systemctl restart foundationdb
cat /etc/foundationdb/fdb.cluster | gcloud beta runtime-config configs variables \
  set fdb-clusterfile-content --config-name "{config_name}"
gcloud beta runtime-config configs variables set "fdb-machines/{vm_name}" "1" \
  --config-name "{config_name}" --is-text
"""

FOLLOWER_TEMPLATE = """
#!/bin/bash
{install_packages}
# Wait until it is this VM's turn to join the cluster.
gcloud beta runtime-config configs waiters create "waiter-{vm_name}" \
  --config-name "{config_name}" --success-cardinality-path fdb-machines \
  --success-cardinality-number {required_count} --timeout {timeout}
gcloud beta runtime-config configs variables get-value fdb-clusterfile-content \
  --config-name "{config_name}" > /etc/foundationdb/fdb.cluster
systemctl start foundationdb
gcloud beta runtime-config configs variables set "fdb-machines/{vm_name}" "1" \
  --config-name "{config_name}" --is-text
"""


def GenerateConfig(context):
    vm_index = context.properties['initOrder'].index(context.env['name'])
    if vm_index == 0:
        script = LEADER_TEMPLATE.format(
            install_packages=INSTALL_PACKAGES,
            config_name=context.properties['configName'],
            vm_name=context.env['name'])
    else:
        script = FOLLOWER_TEMPLATE.format(
            install_packages=INSTALL_PACKAGES,
            vm_name=context.env['name'],
            config_name=context.properties['configName'],
            required_count=vm_index,
            timeout=300 * vm_index)

    resources = [{
        'name': context.env['name'],
        'type': 'compute.v1.instance',
        'properties': {
            'zone': context.properties['zone'],
            'machineType': '/'.join([COMPUTE_URL_BASE, 'projects',
                                    context.env['project'], 'zones',
                                    context.properties['zone'], 'machineTypes',
                                    context.properties['machineType']]),
            'serviceAccounts': [{
                'email': context.properties['serviceAccount'],
                'scopes': ['https://www.googleapis.com/auth/cloudruntimeconfig']
                }
            ],
            'disks': [{
                'deviceName': 'boot',
                'type': 'PERSISTENT',
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': '/'.join([COMPUTE_URL_BASE, 'projects',
                                            'ubuntu-os-cloud/global',
                                            'images/family/ubuntu-1804-lts'])
                }
            }],
            'networkInterfaces': [{
                'network': '$(ref.' + context.properties['network'] + '.selfLink)',
                'accessConfigs': [{
                    'name': 'External NAT',
                    'type': 'ONE_TO_ONE_NAT'
                }]
            }],
            'metadata': {
                'items': [{'key': 'startup-script', 'value': script}]
            }
        }
    }]

    return {'resources': resources}
