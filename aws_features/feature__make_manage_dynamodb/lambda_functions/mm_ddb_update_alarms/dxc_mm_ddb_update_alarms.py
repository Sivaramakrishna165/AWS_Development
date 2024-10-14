'''

Created as part of [AWSPE-6470]

This function is part of Dynamodb Make Manage. 
It will help the users to modify the alarm properties and also to create new alarms apart from the default alarms that are created by make manage.
This function has a trigger from the FtMMDynamodbAlarms dynamodb stream. The Dynamodb stream triggers the lamdba whenever it captures a change.
The function will only look for the event type "MODIFY".If the received alarm properties are for new alarm, then a new alarm will be created. If the received properties are for the existing alarms, then the properties will be updated.
If there is no change in the property, then the function will not perform any updates.

Changegable properties: ['ComparisonOperator','AlarmActions', 'ActionsEnabled', 'AlarmDescription', 'Statistic', 'Period', 'EvaluationPeriods', 'Threshold']

    Author : Arunkumar Chandrasekar
    CreationDate : 10 Mar 2023
    ModifiedDate : 19 May 2023

'''

import json, os
import boto3
from botocore.config import Config
from dynamodb_json import json_util as ddb_json
from boto_helper import boto_helper

boto_obj = boto_helper()
ddb_alarms_table = os.environ['MMDdbAlarmsTableName']
alarm_topic = os.environ['CommonIncidentTopic']

def chk_if_alarm_upt_required(existing, new):
    try:
        bln_result = False
        str_keys_to_compare = ['ComparisonOperator', 'AlarmActions', 'ActionsEnabled', 'AlarmDescription', 'Statistic']
        int_keys_to_compare = ['Period', 'EvaluationPeriods', 'Threshold']
        for key in int_keys_to_compare:
            if(key not in existing):
                continue
            if(int(existing[key]) != int(new[key])):
                print('There is a difference in metric - "{}" old-value "{}" required-value "{}"'.format(key, existing[key], new[key]))
                bln_result = True
        
        for key in str_keys_to_compare:
            if(key not in existing):
                 continue
            if(str(existing[key]) != str(new[key])):
                print('There is a difference in metric - "{}" old-value "{}" required-value "{}"'.format(key, existing[key], new[key]))
                bln_result = True
        return bln_result
    except Exception as e:
        print('Error compare_alarm_metrics() - ',e)
        raise e


def lambda_handler(event, context):

    try:
        print('Event - ', event)
        dynamo_item = ddb_json.loads(event['Records'][0])
        event_type = dynamo_item['eventName']
        print("Event Type-", event_type)
        
        if(event_type.upper() == 'MODIFY' and 'Alarms' in dynamo_item['dynamodb']['NewImage']):
            tableName = dynamo_item['dynamodb']['NewImage']['TableName']
            alarms = dynamo_item['dynamodb']['NewImage']['Alarms']

            for alarm in alarms:
                try:
                    for dim in alarm['Dimensions']:
                        if dim['Name']=='TableName':
                            dim['Value']=tableName
                    
                    alarm_name='_'.join(["MM",alarm['Namespace'].lower().replace("/",""),dim['Value'],alarm['MetricName']])
                    alarm['AlarmName'] = alarm_name
                    if('AlarmActions' in alarm and len(alarm['AlarmActions']) == 0):
                        alarm['AlarmActions']=[alarm_topic]
                        
                    print("New/Update alarm properties\n",alarm)
                    alarm_check_result=boto_obj.alarm_check(alarm_name)
                    
                    if not alarm_check_result:
                        boto_obj.create_alarm(alarm, 'Create')
                    else:
                        existing_alarm_prop = boto_obj.get_alarm(alarm_name)
                        print("Existing alarm properties\n", existing_alarm_prop)
                        if(chk_if_alarm_upt_required(existing_alarm_prop, alarm)):
                                boto_obj.create_alarm(alarm, 'Update')
                        else:
                            print('No updates required for Alarm - ',alarm_name)
                        
                except Exception as e:
                    print('ERROR while creating/updating alarm - {} ... error - {}'.format(alarm,str(e)))
                
        else:
            print('The event type is {}. Hence, Doing Nothing'.format(event_type))        
                            
    except Exception as e:
        print('Error lambda_handler() ', e)
        raise