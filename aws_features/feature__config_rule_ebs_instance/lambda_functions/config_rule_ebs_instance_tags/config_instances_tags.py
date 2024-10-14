#
#  Ensure all Instances have the following tag keys with values:
# - Name
# - Application
# - InstanceName
# - Environment
# - Owner
# - Project
# - Compliance
#
# Trigger Type: Change Triggered
# Scope: AWS::EC2::Instance
# Accepted Parameter: instanceRequiredTags: requiredTagKey1,requiredTagKey2,requiredTagKey3,....
# Example Values: "instanceRequiredTags: Name,Environment,Owner,...."
#

from __future__ import print_function
from datetime import tzinfo, datetime, timedelta
import json
import boto3
import time
import random
import dateutil.parser
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


class InstanceTagEvaluation:
    def __init__(self):
        self.ec2 = boto3.client('ec2')
        self.config = boto3.client('config')
        self.ddb = boto3.resource('dynamodb')

    def is_applicable(self, config_item, event):
        status = config_item['configurationItemStatus']
        event_left_scope = event['eventLeftScope']
        test = ((status in ['OK', 'ResourceDiscovered']) and
                event_left_scope is False)
        return test

    def getTagValue(self, tagList, tagName):
        for tag in tagList:
            if tag['Key'] == tagName :
                value = tag["Value"]
                return value.lower()
        return ''

    def getInstanceTagNames(self, tagList):
        instanceTagNames = []
        for tag in tagList:
            instanceTagNames.append(tag['Key'])
        return instanceTagNames

    def getEbsInstInstanceIdListToSkip(self, tbl_name, partition_key, partition_value):
        try:
            table = self.ddb.Table(tbl_name)
            get_item_response = table.get_item(Key={partition_key: partition_value})
            instance_list = get_item_response['Item']['FeatureParams']['pFtEbsInstInstanceIdListToSkip']['Default']
            return instance_list
        except Exception as e:
            print(str(e) + "exception in getEbsInstInstanceIdListToSkip")    

    def check_instance_tags(self, config_item, rules):
        # unmodifed Config Rules are a list, modified Config Rules are a string
        rule_is_string = isinstance(rules['instanceRequiredTags'], str)
        if rule_is_string:
            required_tags =  rules['instanceRequiredTags'].replace('\\','').replace('"','').replace(']','').replace('[','')
            required_tags = required_tags.split(',')
        else:
            required_tags = rules['instanceRequiredTags']
        print("rules are ", rules)
        evaluations = []
        OSServiceLevel = ''
        Patch_Group = ''
        reservations = self.retrieve_reservations()
        print("Required Tags are: ", required_tags)
        instanceId_to_skip = self.getEbsInstInstanceIdListToSkip('AccountFeatureDefinitions', 'Feature', 'ConfigRuleEBSInstance')
        instanceId_List_to_skip = instanceId_to_skip.split(',')        
        for res in reservations:
            for instance in res['Instances']:
                if instance['InstanceId'] not in instanceId_List_to_skip:                
                    creation_time = instance['LaunchTime']
                    if self.is_older_than_one_hour(creation_time):
                        valueCompliance = 'COMPLIANT'
                        compliance_value = 'NON_COMPLIANT'

                        if 'Tags' in instance:
                            print('Instance Evaluated: ' + str(instance['InstanceId']))
                            instanceTagList = instance['Tags']
                            subnet_info = self.ec2.describe_subnets(SubnetIds=[instance['SubnetId']])
                            subnetTagList = subnet_info['Subnets'][0]['Tags']
                            instance_tags = self.getInstanceTagNames(instanceTagList)

                            SubnetApplyPatchingTagvalue = self.getTagValue(subnetTagList, 'ApplyPatching')

                            PatchGroupTagValue = self.getTagValue(instanceTagList, 'Patch Group')

                            if SubnetApplyPatchingTagvalue == 'true':
                                if not PatchGroupTagValue:
                                    valueCompliance = 'NON_COMPLIANT'
                                    print('non-compliance: If subnet tag "ApplyPatching" is "true" the instance tag "Patch Group" value must not be empty')

                            if valueCompliance == 'NON_COMPLIANT':
                                compliance_value = valueCompliance
                                print(str(instance['InstanceId']) + ' is non-compliant')
                            elif instance_tags and all(x in instance_tags for x in required_tags):
                                compliance_value = 'COMPLIANT'
                                print(str(instance['InstanceId']) + ' is compliant')
                            else:
                                missing_tags = list(set(required_tags) - set(instance_tags))
                                print(str(instance['InstanceId']) + ' is non-compliant')
                                print('Missing tags: ' + str(missing_tags))
                        else:
                            print('Instance Evaluated: ' + str(instance['InstanceId']))
                            print(str(instance['InstanceId']) + ' is non-compliant')
                            print('Missing tags: ' + str(required_tags))

                        evaluations.append(
                            {
                                'Annotation': 'Evaluation of Instance ID: ' + instance['InstanceId'],
                                'ComplianceResourceType': 'AWS::EC2::Instance',
                                'ComplianceResourceId': instance['InstanceId'],
                                'ComplianceType': compliance_value,
                                'OrderingTimestamp': datetime.now(utc)
                            }
                        )
                    else:
                        print('Instance: ' + instance['InstanceId'] +
                          ' is less than one hour old and was not evaluated for compliance.')
        return evaluations

    def retrieve_reservations(self):
        marker = ''
        reservations = []
        response_iterator = ''
        while marker is not None:
            response_iterator = self.ec2.describe_instances(
                Filters=[
                    {
                        'Name': 'instance-state-name',
                        'Values': [
                            'running'
                        ],
                    },
                ],
                MaxResults=300,
                NextToken=marker
            )
            reservations = self.merge_lists(response_iterator['Reservations'], reservations)
            try:
                marker = response_iterator['NextToken']
            except KeyError:
                print('Last DescribeInstances response element processed')
                break
        return reservations

    def merge_lists(self, list1, list2):
        merged = []
        merged = list2 + [x for x in list1 if x not in list2]
        return merged

    def evaluate_compliance(self, config_item, rule_parameters):
        if config_item['resourceType'] != 'AWS::EC2::Instance' or config_item['configurationItemStatus'] in ['ResourceDeletedNotRecorded', 'ResourceNotRecorded', 'ResourceDeleted']:
            return 'NOT_APPLICABLE'

        evaluations = self.check_instance_tags(config_item, rule_parameters)

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