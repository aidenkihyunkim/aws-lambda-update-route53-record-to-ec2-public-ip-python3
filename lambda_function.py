import os
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

""" Default values """
DNS_TAG_KEY = 'Route53FQDN'
DNS_RECORD_TYPE = 'CNAME'
DNS_RECORD_TTL = 60

def update_route53_record(region, instance_id, dns_tag_key, dns_record_type, dns_record_ttl):
    """
    update function
    """
    dns_record_type = dns_record_type.upper()

    """ Get EC2 Description """
    ec2 = boto3.client('ec2', region_name=region)
    ec2_desc_res = ec2.describe_instances( InstanceIds=[ instance_id ] )
    if (not 'Reservations' in ec2_desc_res) or (len(ec2_desc_res['Reservations']) < 1) or (len(ec2_desc_res['Reservations'][0]['Instances']) < 1):
        raise RuntimeError('Getting EC2 instance information failure. Instance Id: ' + instance_id) from error
    if (ec2_desc_res['Reservations'][0]['Instances'][0]['State']['Name'] != 'running'):
        logger.warning('EC2 state is not running. Current state: ' + ec2_desc_res['Reservations'][0]['Instances'][0]['State']['Name'])
        return
    ec2_public_dns = ec2_desc_res['Reservations'][0]['Instances'][0]['PublicDnsName']
    ec2_public_ip = ec2_desc_res['Reservations'][0]['Instances'][0]['PublicIpAddress']

    """ Get EC2 Tags """
    ec2_tags_res = ec2.describe_tags( Filters=[
        {'Name': 'resource-id', 'Values': [ instance_id ]},
        {'Name': 'key', 'Values': [ dns_tag_key ]}
    ] )
    if (not 'Tags' in ec2_tags_res) or (len(ec2_tags_res['Tags']) < 1 ):
        logger.warning('EC2 instance has no DNS tag. Instance Id: ' + instance_id)
        return
    dns_record_name = ec2_tags_res['Tags'][0]['Value']
    if (dns_record_name[-1] == '.'):
        dns_record_name = dns_record_name[:-1]

    """ Check DNS name """
    dns_record_names = dns_record_name.split('.')
    if (len(dns_record_names) < 3 ):
        raise RuntimeError('The FQDN must over 3 levels at least. Instance Id: ' + instance_id + ', ' + dns_tag_key + ': ' + dns_record_name) from error

    """ Get all hosted zones from Route53 """
    route53 = boto3.client('route53', region_name=region)
    zones_res = route53.list_hosted_zones()
    all_zones = zones_res['HostedZones']
    if (zones_res['IsTruncated']):
        while zones_res and (not zones_res['IsTruncated']):
            zones_res = route53.list_hosted_zones(Marker=zones_res['NextMarker'])
            all_zones = all_zones + zones_res['HostedZones']

    """ Find Route53 zone """
    zone_id = None
    for i in range(1, len(dns_record_names)-1):
        cur_zone_name = '.'.join(dns_record_names[i:len(dns_record_names)+1]) + '.'
        cur_zone_matches = [zone for zone in all_zones if (zone['Name']==cur_zone_name)]
        if (len(cur_zone_matches) > 0):
            zone_id = cur_zone_matches[0]['Id']
            break
    if (not zone_id):
        raise RuntimeError('Route53 zone is not found. DNS name: ' + dns_record_name) from error

    """ Update Route53 record record """
    route53.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            'Changes': [
                {
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': dns_record_name + '.',
                        'Type': dns_record_type,
                        'ResourceRecords': [{'Value': (ec2_public_dns if (dns_record_type=='CNAME') else ec2_public_ip) }],
                        'TTL': dns_record_ttl
                    }
                }
            ]
        }
    )
    logger.info('The Route53 record updated successfully. ' + dns_record_name + ': [' + dns_record_type + '] ' + (ec2_public_dns if (dns_record_type=='CNAME') else ec2_public_ip))
    return

def lambda_handler(event, context):
    """
    main function
    """
    region = os.environ.get("region")
    instance_id = os.environ.get("instance_id")
    dns_tag_key = os.environ.get("dns_tag_key") if os.environ.get("dns_tag_key") else DNS_TAG_KEY
    dns_record_type = os.environ.get("dns_record_type") if os.environ.get("dns_record_type") else DNS_RECORD_TYPE
    dns_record_ttl = int(os.environ.get("dns_record_ttl")) if os.environ.get("dns_record_ttl") else DNS_RECORD_TTL

    if (('region' in event) and event['region']):
        region = str(event['region'])
    if (not region):
        raise RuntimeError('Parameter "region" is not defined.') from error

    if (('detail' in event) and ('instance-id' in event['detail']) and event['detail']['instance-id']):
        instance_id = str(event['detail']['instance-id'])
    if (not instance_id):
        raise RuntimeError('Parameter "instance-id" is not defined.') from error

    if (('state' in event['detail']) and event['detail']['state'] and (event['detail']['state'] != 'running')):
        logger.warning('EC2 state is not running. Current state: ' + event['detail']['state'])
        return

    try:
        update_route53_record(region, instance_id, dns_tag_key, dns_record_type, dns_record_ttl)
    except Exception as error:
        logger.exception(error)
    return
