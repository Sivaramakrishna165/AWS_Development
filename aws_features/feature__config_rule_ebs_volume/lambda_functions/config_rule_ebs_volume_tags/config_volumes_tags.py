# Ensure all volumes have the following tag keys with values:
# - Name
# - Environment
# - Owner
# - Project
# - Compliance
#
# Trigger Type: Change Triggered
# Scope: AWS::EC2::Volume
# Accepted Parameter: volumeRequiredTags: requiredTagKey1,requiredTagKey2,requiredTagKey3,....
# Example Values: "volumeRequiredTags: Name,Environment,Owner,...."
#

from __future__ import print_function
from datetime import tzinfo, datetime, timedelta
import json
import boto3
import time
import random
import dateutil.parser
from botocore.config import Config
from boto3.dynamodb.conditions import Key

ZERO = timedelta(0)

class UTC(tzinfo):
    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

utc = UTC()

class VolumeTagEvaluation:
    def __init__(self):
        self.ec2 = boto3.client('ec2')
        self.config = boto3.client('config')
        self.ddb = boto3.resource('dynamodb', config=Config(retries=dict(max_attempts=10, mode='standard')))

    def is_applicable(self, config_item, event):
        status = config_item['configurationItemStatus']
        event_left_scope = event['eventLeftScope']
        test = ((status in ['OK', 'ResourceDiscovered']) and
                event_left_scope is False)
        return test

    def check_volume_tags(self, config_item, rules):
        # unmodifed Config Rules are a list, modified Config Rules are a string
        rule_is_string = isinstance(rules['volumeRequiredTags'], str)
        if rule_is_string:
            required_tags = rules['volumeRequiredTags'].replace('\\', '').replace('"', '').replace(']', '').replace('[', '')
            required_tags = required_tags.split(',')
        else:
            required_tags = rules['volumeRequiredTags']

        print("rules are ", rules)

        evaluations = []
        volumes = self.retrieve_volumes()
        volumeId_to_skip = self.get_ebs_vol_volume_id_list_to_skip('AccountFeatureDefinitions', 'Feature', 'ConfigRuleEbsVolume')
        volumeId_List_to_skip = volumeId_to_skip.split(',')
        print(f"Volumes to skip: {volumeId_List_to_skip}")
        print("required_tags are ", required_tags)
        for volume in volumes:
            if volume['VolumeId'] in volumeId_List_to_skip:
                print(f"Skipping volume {volume['VolumeId']} as it is in the skip list.")
                continue

            creation_time = volume['CreateTime']
            if self.is_older_than_one_hour(creation_time):
                compliance_value = 'NON_COMPLIANT'
                if 'Tags' in volume:
                    volume_tags = []
                    print('Volume Evaluated: ' + str(volume['VolumeId']))
                    for tag in volume['Tags']:
                        for key, value in tag.items():
                            if key == 'Key':
                                volume_tags.append(value)
                    print("volume_tags are ", volume_tags)
                    if volume_tags and all(x in volume_tags for x in required_tags):
                        compliance_value = 'COMPLIANT'
                        print(str(volume['VolumeId']) + ' is compliant')
                    else:
                        # missing_tags = list(set(rules['volumeRequiredTags']) - set(volume_tags))
                        missing_tags = list(set(required_tags) - set(volume_tags))
                        print(str(volume['VolumeId']) + ' is non-compliant')
                        print('Missing tags: ' + str(missing_tags))
                else:
                    print('Volume Evaluated: ' + str(volume['VolumeId']))
                    print(str(volume['VolumeId']) + ' is non-compliant')
                    # print('Missing tags: ' + str(rules['volumeRequiredTags']))
                    print('Missing tags: ' + str(required_tags))

                evaluations.append(
                    {
                        'Annotation': 'Evaluation of Volume ID: ' + volume['VolumeId'],
                        'ComplianceResourceType': 'AWS::EC2::Volume',
                        'ComplianceResourceId': volume['VolumeId'],
                        'ComplianceType': compliance_value,
                        'OrderingTimestamp': datetime.now(utc)
                    }
                )
            else:
                print('Volume: ' + volume['VolumeId'] +
                      ' is less than one hour old and was not evaluated for compliance.')

        return evaluations

    def retrieve_volumes(self):
        marker = ''
        volumes = []
        response_iterator = ''
        while marker is not None:
            response_iterator = self.ec2.describe_volumes(
                Filters=[
                    {
                        'Name': 'status',
                        'Values': [
                            'available',
                            'in-use'
                        ],
                    },
                ],
                MaxResults=300,
                NextToken=marker
            )
            volumes = self.merge_lists(response_iterator['Volumes'], volumes)
            try:
                marker = response_iterator['NextToken']
            except KeyError:
                print('Last DescribeVolumes response element processed')
                break
        return volumes

    def merge_lists(self, list1, list2):
        merged = []
        merged = list2 + [x for x in list1 if x not in list2]
        return merged

    def evaluate_compliance(self, config_item, rule_parameters):
        if config_item['resourceType'] != 'AWS::EC2::Volume' or config_item['configurationItemStatus'] in ['ResourceDeletedNotRecorded', 'ResourceNotRecorded', 'ResourceDeleted']:
            return 'NOT_APPLICABLE'

        evaluations = self.check_volume_tags(config_item, rule_parameters)

        return evaluations

    def process_evaluations(self, evaluations):
        eval_max = 99
        for i in range(0, len(evaluations), eval_max):
            yield evaluations[i:i+eval_max]

    def is_older_than_one_hour(self, creation_time):
        timestamp = str(creation_time)
        creation_time_seconds_since_epoch = dateutil.parser.parse(timestamp).strftime('%s')
        now = time.strftime('%s')
        total_seconds_since_creation = int(now) - int(creation_time_seconds_since_epoch)
        if total_seconds_since_creation > 3600:
            return True
        else:
            return False

    def get_ebs_vol_volume_id_list_to_skip(self, tbl_name, partition_key, partition_value):
        try:
            table = self.ddb.Table(tbl_name)
            get_item_response = table.get_item(Key={partition_key: partition_value})
            volume_list = get_item_response['Item']['FeatureParams']['pFtEbsVolVolumeIdListToSkip']['Default']
            return volume_list
        except Exception as e:
            print(f"{str(e)} exception in getEbsVolVolumeIdListToSkip")
            return ""

    def handler_impl(self, event, context):
        invoking_event = json.loads(event['invokingEvent'])
        rule_parameters = json.loads(event['ruleParameters'])

        evaluations = None
        if self.is_applicable(invoking_event['configurationItem'], event):
            evaluations = self.evaluate_compliance(
                invoking_event['configurationItem'], rule_parameters)

        if not evaluations:
            print('No Evaluations Present')
        else:
            timeout = int(time.time()) + 3*int(1)
            chunked_evaluations = self.process_evaluations(evaluations)
            for evals in chunked_evaluations:
                response = self.config.put_evaluations(
                    Evaluations=evals,
                    ResultToken=event['resultToken'])

                if 'FailedEvaluations' in response and response['FailedEvaluations']:
                    error_message = ("Failed to report all evaluations "
                                     "successfully to the AWSConfig service. "
                                     "Failed: " + str(response['FailedEvaluations']))
                    raise Exception(error_message)

                sleep_time = min(int(timeout), random.uniform(2, 2*3))
                print("Sleep " + str(sleep_time) + " seconds before next request..")
                time.sleep(sleep_time)
