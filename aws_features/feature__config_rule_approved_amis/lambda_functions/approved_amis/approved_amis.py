#
# Ensure instances are launched from AMIs with one of the following tag keys and values:
#  - Environment:Production
#  - Environment:Staging
#  - Environment:QA
#
# Trigger Type: Change Triggered
# Scope: AWS::EC2::Instance
# Accepted Parameter: amisByTagKeyAndValue: requiredKey1:requiredTag1....
# Example Valumes: "amisByTagKeyAndValue: Environment:Production,Environment:Staging,..
#


from __future__ import print_function
import boto3
import json
import re
import time
import dateutil.parser
from boto3.dynamodb.conditions import Key

ddb = boto3.resource('dynamodb')

def getConfigApprovedAmisListToSkip(tbl_name, partition_key, partition_value):
    try:
        table = ddb.Table(tbl_name)
        get_item_response = table.get_item(Key={partition_key: partition_value})
        config_approved_amis_list = get_item_response['Item']['FeatureParams']['pFtApprAmiAmiListToSkip']['Default']
        return config_approved_amis_list
    except Exception as e:
        print(str(e) + "exception in getconfigApprovedAmisListToSkip")

def is_applicable(config_item, event):
    print("CONFIG_ITEM - ", config_item)
    print("EVENT - ", event)
    config_approved_amis_to_skip = getConfigApprovedAmisListToSkip('AccountFeatureDefinitions', 'Feature', 'ConfigRuleApprovedAmis')
    config_approved_amis_List_to_skip = config_approved_amis_to_skip.split(',')  
    print("AMIIds to be skipped as per config rule ====> ", config_approved_amis_to_skip)
    status = config_item['configurationItemStatus']
    event_left_scope = event['eventLeftScope']

    # Check if the 'configuration' field is not None before accessing its properties
    if config_item['configuration'] is not None:
        if config_item['configuration']['imageId'] in config_approved_amis_List_to_skip:
            event_left_scope = True
    test = ((status in ['OK', 'ResourceDiscovered']) and event_left_scope == False)
    return test    

def is_ami_approved(config_item, rules):
    compliance_result = ""
    approved_tags = rules['amisByTagKeyAndValue']
    ec2 = boto3.resource('ec2')
    print('Tags of the following AMI evaulated: ' + str(config_item['configuration']['imageId']))
    ami = ec2.Image(config_item['configuration']['imageId'])
    if ami.tags:
        for tag in ami.tags:
            tag_match = False
            value_match = False
            for key,value in tag.items():
                for approved_tag in approved_tags:
                    tag_k,tag_v = approved_tag.split(':')
                    if (key == 'Key') and (value == tag_k):
                        tag_match = True
                    elif (key == 'Value') and (value == tag_v):
                        value_match = True
                if (value_match == True) and (tag_match == True):
                    compliance_result = "AMI has approved tag."
                    print('AMI has approved tag.')
                    break

    if compliance_result == "":
        return None

    return compliance_result

def evaluate_compliance(config_item, rule_parameters):
    if (config_item['resourceType'] != 'AWS::EC2::Instance'):
        return 'NOT_APPLICABLE'
    for tag in rule_parameters['amisByTagKeyAndValue']:
        result = re.match('([A-Za-z]+[0-9]*[+-=._/@\sA-Za-z]*):([A-Za-z]+[0-9]*[+-=._:/@\s,A-Za-z]*)',
                      tag)
        if result:
            print('amisByTagKeyAndValue parameter in correct format.')
        else:
            raise Exception('Incorrect format for amisByTagKeyAndValue parameter.')

    approved_results = is_ami_approved(config_item, rule_parameters)

    if approved_results:
        return 'COMPLIANT'

    return 'NON_COMPLIANT'

def lambda_handler(event, context):
    invoking_event = json.loads(event['invokingEvent'])
    rule_parameters = json.loads(event['ruleParameters'])

    compliance_value = 'NOT_APPLICABLE'

    if is_applicable(invoking_event['configurationItem'], event):
        compliance_value = evaluate_compliance(
                invoking_event['configurationItem'], rule_parameters)

    config = boto3.client('config')
    response = config.put_evaluations(
       Evaluations=[
           {
               'ComplianceResourceType': invoking_event['configurationItem']['resourceType'],
               'ComplianceResourceId': invoking_event['configurationItem']['resourceId'],
               'ComplianceType': compliance_value,
               'OrderingTimestamp': invoking_event['configurationItem']['configurationItemCaptureTime']
           },
       ],
      ResultToken=event['resultToken'])
