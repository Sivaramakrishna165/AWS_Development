#
# Ensure all snapshots have the following tag keys with values:
# - Application
# - Name
# - Environment
# - InstanceName
# - Owner
# - Project
# - DeleteOn
#
# Trigger Type: Change Triggered
# Scope: AWS::EC2::Volume
# Accepted Parameter: snapshotRequiredTags: requiredTagKey1,requiredTagKey2,requiredTagKey3,....
# Example Values: "snapshotRequiredTags: Name,Environment,Owner,...."
#
# Change 18-june-2020 Return one compliance value per EC2 volume, not one compliance value per snapshot.

from __future__ import print_function
from datetime import tzinfo, datetime, timedelta
import json
import boto3
import time
import random
import dateutil.parser
from botocore.config import Config
from boto3.dynamodb.conditions import Key
import copy

ZERO = timedelta(0)
class UTC(tzinfo):
    def utcoffset(self, dt):
        return ZERO
    def tzname(self, dt):
        return "UTC"
    def dst(self, dt):
        return ZERO
utc = UTC()

def is_applicable(config_item, event):
    status = config_item['configurationItemStatus']
    event_left_scope = event['eventLeftScope']
    test = ((status in ['OK', 'ResourceDiscovered']) and 
            event_left_scope is False)
    return test

def check_snapshot_tags(config_item, rules, ec2_volumes):
    # unmodifed Config Rules are a list, modified Config Rules are a string
    rule_is_string = isinstance(rules['snapshotRequiredTags'], str)
    if rule_is_string:
        required_tags =  rules['snapshotRequiredTags'].replace('\\','').replace('"','').replace(']','').replace('[','')
        required_tags = required_tags.split(',')
    else:
        required_tags = rules['snapshotRequiredTags']
    evaluations = []
    print("Required Tags: ", required_tags)
    for obj in ec2_volumes:
        print('{} - {}'.format(obj, ec2_volumes[obj]))
        for vol in ec2_volumes[obj]:
            snapshots = retrieve_snapshots(vol)
            if snapshots:
                compliance_value = None
                annotation =  None
                for snapshot in snapshots:
                    if 'Tags' in snapshot:
                        snapshot_tags = []
                        print('Snapshot Evaluated: ' + str(snapshot['SnapshotId']))
                        for tag in snapshot['Tags']:
                            for key,value in tag.items():
                                if key == 'Key':
                                    snapshot_tags.append(value)
                        if all(x in snapshot_tags for x in required_tags):
                            compliance_value = 'COMPLIANT'
                            annotation = "All snapshots compliant"
                            print(str(snapshot['SnapshotId']) + ' is compliant')
                        else:
                            missing_tags = list(set(required_tags) - set(snapshot_tags))
                            print(str(snapshot['SnapshotId']) + ' is non-compliant')
                            print('Missing tags: ' + str(missing_tags))
                            compliance_value = 'NON_COMPLIANT'
                            annotation = 'Evaluation of Snapshot ID: ' + snapshot['SnapshotId'] + ' is non-compliant, stopping evaluations for this volume_id'
                            break  #don't need to check rest of snapshots,One failure makes the volume non-compliant
                        
                if (compliance_value and annotation):
                    print('Volume ', vol, ' completed: ', compliance_value )
                    evaluations.append(
                        {
                            'Annotation': annotation,
                            'ComplianceResourceType': 'AWS::EC2::Volume',
                            'ComplianceResourceId': vol,
                            'ComplianceType': compliance_value,
                            'OrderingTimestamp': datetime.now(utc)
                        }
                    )
                else:
                    print('Bad logic-complaince value seen as None, aborting')
            else:
                print('Snapshots not present')

    return evaluations

def merge_lists(list1, list2):
    merged = []
    merged = list2 + [x for x in list1 if x not in list2]
    return merged

def retrieve_snapshots(volume_id):
    marker = ''
    snapshots = []
    response_iterator = ''
    ec2 = boto3.client('ec2')
    while marker is not None:
        response_iterator = ec2.describe_snapshots(
            Filters=[
                {
                    'Name': 'status',
                    'Values': [
                        'completed',
                    ]
                },
                {
                    'Name': 'volume-id',
                    'Values': [
                        volume_id,
                    ]
                }
            ],
            OwnerIds=['self'],
            MaxResults=300,
            NextToken=marker
        )
        snapshots = merge_lists(response_iterator['Snapshots'], snapshots)
        try:
            marker = response_iterator['NextToken']
        except KeyError:
            print('Last DescribeSnapshots response element processed')
            break

    return snapshots

def list_config_discovered_volumes(config):
    volumes = []
    ldr_pagination_token = ''
    while True:
        discovered_volumes_response = config.list_discovered_resources(
            resourceType='AWS::EC2::Volume',
            nextToken=ldr_pagination_token
        )
        volumes.extend(discovered_volumes_response['resourceIdentifiers'])
        if 'nextToken' in discovered_volumes_response:
            ldr_pagination_token = discovered_volumes_response['nextToken']
        else:
            break
    
    return volumes

def describe_vols_for_instances(ec2):
    extra_args = {}
    extra_args['MaxResults'] = 100
    volumes = {}
    while True:
        response = ec2.describe_volumes(**extra_args)
        for obj_att in response['Volumes']:
            for obj in obj_att['Attachments']:
                if(obj['InstanceId'] not in volumes):
                    volumes[obj['InstanceId']] = []
                volumes[obj['InstanceId']].append(obj['VolumeId'])            
        
        if 'NextToken' in response:
            extra_args = response['NextToken']
        else:
            break
    return volumes

def getEbsSnapVolumeIdListToSkip(tbl_name, partition_key, partition_value, ddb):
    try:
        table = ddb.Table(tbl_name)
        get_item_response = table.get_item(Key={partition_key: partition_value})
        volume_list = get_item_response['Item']['FeatureParams']['pFtEbsSnapVolumeIdListToSkip']['Default']
        return volume_list
    except Exception as e:
        print(str(e) + "exception in getEbsSnapVolumeIdListToSkip") 

def evaluate_compliance(config_item, rule_parameters, volumes):
    if config_item['resourceType'] != 'AWS::EC2::Volume' or config_item['configurationItemStatus'] in ['ResourceDeletedNotRecorded', 'ResourceNotRecorded', 'ResourceDeleted']:
        return 'NOT_APPLICABLE'

    evaluations = check_snapshot_tags(config_item, rule_parameters, volumes)

    return evaluations

def process_evaluations(evaluations):
    eval_max = 99
    for i in range(0, len(evaluations), eval_max):
        yield evaluations[i:i+eval_max]

def lambda_handler(event, context):
    print('Event Received',event)
    invoking_event = json.loads(event['invokingEvent'])
    rule_parameters = json.loads(event['ruleParameters'])
    config_rule_name =  event['configRuleName']
    
    exp_config=Config(retries=dict(max_attempts=10,mode='standard'))
    config = boto3.client('config', config=exp_config)
    ec2 = boto3.client('ec2', config=exp_config)
    ddb = boto3.resource('dynamodb', config=exp_config)
    config_disc_volumes = list_config_discovered_volumes(config)
    config_disc_only_volumes = [obj['resourceId'] for obj in config_disc_volumes]
    ec2_volumes = describe_vols_for_instances(ec2)
    ec2_volumes_itr = copy.deepcopy(ec2_volumes)
    volumeId_to_skip = getEbsSnapVolumeIdListToSkip('AccountFeatureDefinitions', 'Feature', 'ConfigRuleEbsSnapshot', ddb)
    volumeId_List_to_skip = volumeId_to_skip.split(',')
    print('volume ids to be skipped', volumeId_List_to_skip)
    
    # Filter the volumes and structure the json based on instanceID
    for obj in ec2_volumes_itr:
        for vol in ec2_volumes_itr[obj]:
            if vol not in config_disc_only_volumes or vol in volumeId_List_to_skip:
                ec2_volumes[obj].remove(vol)
                
    if is_applicable(invoking_event['configurationItem'], event):
        evaluations = evaluate_compliance(
               invoking_event['configurationItem'], rule_parameters, ec2_volumes)
    else: evaluations = []

    if not evaluations:
        print('No Evaluations Present')
    else:
        timeout = int(time.time()) + 3*int(1)
        chunked_evaluations = process_evaluations(evaluations)
        for evals in chunked_evaluations:
            response = config.put_evaluations(
                Evaluations = evals,
                ResultToken = event['resultToken'])

            if 'FailedEvaluations' in response and response['FailedEvaluations']:
                error_message = ("Failed to report all evaluations "
                                "successfully to the AWSConfig service. "
                                "Failed: " + str(response['FailedEvaluations']))
                raise Exception(error_message)
            
            sleep_time = min(int(timeout), random.uniform(2, 2*3))
            print("Sleep " + str(sleep_time) + " seconds before next request..")
            time.sleep(sleep_time)