"""

"""

import json
import boto3
import os
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

def stepfunction(step_arn, json_data):
    print("Stepfunction Called")
    statefunction = boto3.client('stepfunctions', config=config)
    try:
        response = statefunction.start_execution(
                            stateMachineArn = step_arn,
                            input = json.dumps(json_data)
                        )
    except Exception as e:
        print("Error stepfunction() - ", e)
        print("Error during stepfunction call")
    else:
        print("Triggered Successfully")

def lambda_handler(event, context):
    print("############ Event Recieved ############")
    print(event)
    print("########################################")
    event_message = json.loads(event['Records'][0]['Sns']['Message'])
    sfn_arn = os.environ['sfn_arn']
    dump_event = {}
    try:
        topic_arn = event['Records'][0]['Sns']['TopicArn']
        message_id = event['Records'][0]['Sns']['MessageId']
        time_stamp = event['Records'][0]['Sns']['Timestamp']
        if (topic_arn.find('rInstanceAlarmTopic') != -1):
            if 'Trigger' in event_message:
                for dim in event_message['Trigger']['Dimensions']:
                    if dim['name'] == 'InstanceId':
                        dump_event['InstanceId'] = dim['value']
                        break
                id_index = event_message['Trigger']['Dimensions'].index(dim)
                event_message['Trigger']['Dimensions'].insert(0,event_message['Trigger']['Dimensions'].pop(id_index))
            dump_event['Event'] = "EC2CloudWatchAlarms"
            dump_event['EventDate'] = time_stamp
            dump_event['MessageId'] = message_id
            dump_event['InitialTriggerDetails'] = event_message

            if 'Trigger' in event_message:
                if event_message["NewStateValue"] != 'OK':
                    stepfunction(sfn_arn, dump_event)
                else:
                    print(f"Not an Alarm. NewStateValue is 'OK'. SelfHeal Step Function not triggered.")
            else:
                print(f"Not an Alarm. 'Trigger' not in 'Message'. SelfHeal Step Function not triggered.")
        elif(topic_arn.find('dxcms-ad-sns-notification') != -1):
            if 'Trigger' in event_message:
                dump_event['Event'] = "LambdaAnomalyDetection"
                dump_event['EventDate'] = time_stamp
                dump_event["resource_id"] = event_message['AlarmName']
                dump_event["AlarmName"] = event_message['AlarmName']
                dump_event["NewStateReason"] = event_message['NewStateReason']

                stepfunction(sfn_arn, dump_event)
            else:
                print(f"Not an Alarm. 'Trigger' not in 'Message'. SelfHeal Step Function not triggered.")
        else:
            raise Exception("Not a valid alarm arn.")

        return event

    except Exception as e:
        print("Error lambda_handler() - ", e)
        print("=======================")
        print("Payload Recived: ",event)