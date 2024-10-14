import boto3
import json
import os
import http.client
from http.client import responses
import urllib3
from botocore.exceptions import ClientError
from botocore.config import Config
import logging

"""
Example Send Lambda Event received:
 {'EventList': [{'eventsourcesendingserver': 'i-0abbb1ebbb73f188c', 'eventsourceexternalid': 'Account: 225992052696, Region: us-west-1', 'severity': 'Critical', 'title': 'FeatureConfigNotificationSe-rSendNotificationState-ABC123', 'longDescription': '{\n  "AWSAccountId": "225992052696",\n  "AlarmDescription": "Non-Compliant Config Resources",\n  "AlarmName": "FeatureConfigNotificationSe-rSendNotificationState-ABC123",\n  "MessageId": "event_MessageId",\n  "NewStateReason": "Non-Compliant Resources: [{\'ResourceId\': \'i-0abbb1ebbb73f188c\', \'Notification\': \'false\', \'ResourceType\': \'AWS::EC2::Instance\', \'ConfigRuleName\': \'FeatureConfigRuleEBSInstanceStack-EB-AWSConfigRule-ABC123\'}, {\'ResourceId\': \'i-0abbb1ebbb73f188c\', \'Notification\': \'false\', \'ResourceType\': \'AWS::EC2::Instance\', \'ConfigRuleName\': \'FeatureConfigRuleApprovedAmisStack-A-AWSConfigRule-ABC123\'}, {\'ResourceId\': \'i-0abbb1ebbb73f188c\', \'Notification\': \'false\', \'ResourceType\': \'AWS::EC2::Instance\', \'ConfigRuleName\': \'FeatureConfigRuleEc2InstanceDetaile-rAWSConfigRule-ABC123\'}, {\'ResourceId\': \'vol-03485c5a5f5c4228e\', \'Notification\': \'false\', \'ResourceType\': \'AWS::EC2::Volume\', \'ConfigRuleName\': \'FeatureConfigRuleEbsVolumeStack-EbsV-AWSConfigRule-ABC123\'}, {\'ResourceId\': \'vol-03485c5a5f5c4228e\', \'Notification\': \'false\', \'ResourceType\': \'AWS::EC2::Volume\', \'ConfigRuleName\': \'FeatureConfigRuleEbsSnapshotStack-Eb-AWSConfigRule-ABC123\'}]",\n  "NewStateValue": "ALARM",\n  "OldStateValue": "OK",\n  "PriorityData": {\n    "Priority": "1"\n  },\n  "Region": "us-east-2",\n  "Trigger": {\n    "ComparisonOperator": "GreaterThanThreshold",\n    "Dimensions": [\n      {\n        "name": "InstanceId",\n        "value": "i-0abbb1ebbb73f188c"\n      }\n    ],\n    "EvaluateLowSampleCountPercentile": "",\n    "EvaluationPeriods": "1",\n    "MetricName": "Config Service: Non-Compliance",\n    "Namespace": "ConfigEvaluations",\n    "Period": "3600",\n    "Region": "us-east-2",\n    "Statistic": "SampleCount",\n    "StatisticType": "Statistic",\n    "Threshold": "0",\n    "TreatMissingData": "",\n    "Unit": "event_Unit"\n  },\n  "default": "required for json format",\n  "original_Timestamp": "2022-06-01T01:02:03.000Z"\n}', 'category': 'AWS CloudWatch', 'application': 'Config Service: Non-Compliance', 'eventsourcecreatedtime': '2022-06-17T18:10:01.520Z', 'incidentCategory': 'Hardware', 'incidentSubcategory': 'Virtual', 'incidentImpact': '1', 'node': 'i-0abbb1ebbb73f188c', 'relatedcihints': 'i-0abbb1ebbb73f188c'}]}

"""

logger = logging.getLogger()
logger.setLevel(logging.INFO)
config=Config(retries=dict(max_attempts=10,mode='standard'))

secmgrname_apidet = os.environ['SECMGR_API_DET']
secmgr_client = boto3.client('secretsmanager',config=config)
sqs_client = boto3.client('sqs',config=config)

Dlq_Url = os.environ['DLQ_URL']

def formatMessage(msg, Dlq_Url):
    try:
        # Complete the formatting of the Agnostic API json input
        except_reason = None
        formatMessage_response = {'formatted_API_message': None, 'reason': None} 
        title = msg['EventList'][0]['title']
        message = title
        snsJson = {}
        snsJson['default'] = message
        snsJson['https'] = json.dumps(msg)
        snsJsonMsg = json.dumps(snsJson)
        ApiEventMsg = snsJson['https']
        print("snsJsonMsg is: ", snsJsonMsg)

    except Exception as e:
        print('Error:formatMessage()-', e)
        except_reason = 'Error in formatMessage' 

    if except_reason is not None:
        send_to_dlq(msg, Dlq_Url)
        formatMessage_response['reason'] = except_reason
        return formatMessage_response
    else:
        formatMessage_response['formatted_API_message'] = ApiEventMsg
        formatMessage_response['reason'] = 'SUCCESS'
        print("formatMessage_response in formatMessage is: ", formatMessage_response) 
        return formatMessage_response


def send_to_ServiceNow(api_message,secmgrname_apidet,Dlq_Url):
    except_reason = None
    try:
        print("api_message is:",api_message)

        ### Check for Agnostic API credentials and create ServiceNow incident if they exist
        print(secmgrname_apidet)
        secret_name = secmgrname_apidet

        if secret_name:

            print('secret_name is not None. Proceed with API call')

            get_secret_value_response = secmgr_client.get_secret_value(
                SecretId=secret_name
            )
            secret_dict = json.loads(get_secret_value_response['SecretString'])

            agnosticAPIUserName = secret_dict['AgnosticAPIUserName']
            agnosticAPIPassword = secret_dict['AgnosticAPIPassword']
            agnosticAPIURL = secret_dict['AgnosticAPIURL']

            #make sure all 3 are present
            if agnosticAPIUserName and agnosticAPIPassword and agnosticAPIURL:
                print('user name, Password and URL present. Proceed with API Trigger')

                http = urllib3.PoolManager()

                headers = urllib3.make_headers(
                    basic_auth="{0}:{1}".format(agnosticAPIUserName, agnosticAPIPassword)
                )

                req = http.request(
                    "POST", agnosticAPIURL, 
                    body=api_message,
                    headers=headers,
                    retries=urllib3.Retry(3, redirect=2,raise_on_status=True,raise_on_redirect=True)
                    )
                http_status = req.status
                http_status_description = responses[http_status]
                if(http_status != 202 and http_status != 200):
                    except_reason = http_status
                    print("except_reason in send_to_ServiceNow is ", except_reason)

                print('Api http_status:',http_status)
                print('http_status_description:',http_status_description)
            else:
                raise ValueError('Agnostic API detail is missing')

    except Exception as e:
        print('Error:send_to_ServiceNow()-', e)
        except_reason = 'Error in send_to_ServiceNow'
    except ValueError as err:
        print('ValueError:send_to_ServiceNow()-', err)
        except_reason = 'Error in send_to_ServiceNow'

    if except_reason is not None:
        send_to_dlq(api_message, Dlq_Url)
        return except_reason
    else:
        return 'SUCCESS'

def send_to_dlq(msg, Dlq_Url):
    msg_string = json.dumps(msg)
    try:
        sqs_response = sqs_client.send_message(
                QueueUrl=Dlq_Url,
                MessageBody=msg_string
            )
    except Exception as e:
        print("Error in send_to_dlq - ", e)


def lambda_handler(event, context):
    try:
        print('Snow Parser Event Received - ',event)
        print('Snow Parser Context Received - ',context)

        ### Process the event 
        formatMessage_result = formatMessage(event, Dlq_Url)
        send_to_ServiceNow_result = send_to_ServiceNow(
            formatMessage_result['formatted_API_message'],
            secmgrname_apidet, Dlq_Url
        )

    except Exception as e:
        print('Error - ',e)
