"""
This lambda is subscribed to the NativeBackupSNSTopic and triggers the step function
whose arn is provided in ENV variable if the valid payload is passed.

This Lambda is a part of Selfheal EC2 NativeBackupFailure
"""

import json
import boto3
import os
import re
import traceback
from datetime import datetime,timezone,timedelta
from boto3.dynamodb.conditions import Key, Attr
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))
dynamodb_resource = boto3.resource('dynamodb',config=config)

table_name = os.environ['table_name']

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
    sfn_arn = os.environ['sfn_arn']
    time_stamp = event['Records'][0]['Sns']['Timestamp']
    dump_event = {'Event': 'Ec2NativeBackupFailure', 'EventDate': time_stamp}
    try:
        linux_level_2_payload = json.loads(event['Records'][0]['Sns']['Message'])
        instance_id = linux_level_2_payload["Instance_id"]
        dump_event["InstanceId"] = instance_id
    except:
        instance_id_pattern = re.compile(r'instance/(i-[a-zA-Z0-9]+)\.?')
        match = instance_id_pattern.search(event['Records'][0]['Sns']['Message'])
        if match:
            instance_id = match.group(1)
            print(f"InstanceId: {instance_id}")
            dump_event["InstanceId"] = instance_id

    if not read_dynamodb_entries(instance_id):
        stepfunction(sfn_arn, dump_event)
    else:
        print("entry found in dynamodb in last 360 mins, step function not triggered")

def read_dynamodb_entries(instance_id):
    try:
        print("read_dynamodb_entries() triggered.")
        table = dynamodb_resource.Table(table_name)
        end_time = datetime.now(timezone.utc).strftime('%FT%TZ')
        start_time = (datetime.now(timezone.utc) - timedelta(minutes = 360)).strftime('%FT%TZ')
        filter_expression = Attr('Event Date').between(start_time,end_time) & Attr('Event').eq("Ec2NativeBackupFailure") & Attr('ImpactedResourceId').eq(instance_id)

        response = table.scan(
            Limit=80,
            FilterExpression=filter_expression
        )
        if response['Items']:
            return True
        else:
            return False
    except Exception as e:
        print("Error read_dynamodb_entries() - ",e)
        print(traceback.format_exc())
        return True