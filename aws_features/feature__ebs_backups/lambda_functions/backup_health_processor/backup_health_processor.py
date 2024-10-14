'''
    This is initial lambda function that gets executed while BackupHealth event rule runs.
    Get all the schedules/rules available for SnapShot creation or EBS Backups creation.
    Describe all the Manages Instances.
    Create a Mapping list with the Instance Id and the corresponding Backup cron expression.
    And also create Mapping list with Instance Id and the last expected cron time, based on the expression.
    Send the Instance Id and expected cron time to the SQS-Queue(dxc-ebsbackup-health-queue) to proceed for further checks.

Created By - Kedarnath Potnuru
Date - 18 July 2023
'''

import boto3
import os
import sys
sys.path.append(os.path.abspath('python_modules'))
from pyawscron import AWSCron
from datetime import date, timedelta, datetime, timezone
import time
import os
import json
from datetime import datetime, timedelta
from botocore.config import Config


config = Config(retries=dict(max_attempts=10,mode='standard'))

# session = boto3.Session(profile_name = 'kedar-c')
# ec2_client = session.client('ec2','eu-west-2')
# events_client = session.client('events','eu-west-2')
# ssm_client = session.client('ssm','eu-west-2')

ec2_client = boto3.client('ec2', config=config)
events_client = boto3.client('events', config=config)
ssm_client = boto3.client('ssm', config=config)
sqs_client = boto3.client('sqs', config=config)

default_sch = 'rSnapshotCreateRule'
custom_sch = 'Snapshot-Schedule'
ssm_param_backups_inci_priority = '/DXC/Backups/IncidentPriority'
queueUrl = os.environ['QueueUrl']

def send_msg_to_queue(queueUrl=None, message=None):
    try:
        sqs_client.send_message(QueueUrl=queueUrl, MessageBody=json.dumps(message))
        print('Message added in the queue ', message)
    except Exception as e:
        print('send_msg_to_queue() error:', e)

def get_ssm_param_value(param):
    try:   
        response = ssm_client.get_parameter(Name = param)
        return response['Parameter']['Value']
    except Exception as e:
        print('Error get_ssm_param_value() - ', e)
        return ''

# Get all the EBS Snapshot create event rules
def list_rules():
    try:
        args = {}
        rules_json = {}
        while True:
            response = events_client.list_rules(**args)
            for rule in response['Rules']:
                # Filter EBS Snapshot Create Events Rules.
                if(default_sch in rule['Name']):
                    rules_json['Default'] = rule['ScheduleExpression']
                elif('Snapshot-Schedule' in rule['Name']):
                    rules_json[rule['Name']] = rule['ScheduleExpression']
                else:
                    continue
            
            if('NextToken' in response):
                args['NextToken'] = response['NextToken']
            else:
                break
        return rules_json
    except Exception as e:
        print('Error list_rules() -',e)
        raise

# Get the last schedule time of the given cron expression
def get_last_sch_time(cron):
    minUTC = datetime.utcnow().minute
    hourUTC = datetime.utcnow().hour
    dateUTC = datetime.utcnow().day
    minUTC = datetime.utcnow().minute
    monthUTC = datetime.utcnow().month
    yearUTC = datetime.utcnow().year
    secUTC = datetime.utcnow().second
    from_dt = datetime(yearUTC, monthUTC, dateUTC, hourUTC, minUTC, secUTC, tzinfo=timezone.utc)

    last_schedule = AWSCron.get_prev_n_schedule(1, from_dt, cron)
    last_schedule_time = time.mktime(last_schedule[0].timetuple())

    return last_schedule_time

def describe_instances(rules, priority=3):
    try:
        date_time = datetime.now()
        instances_lst = []
        params = {}
        params['Filters']= [
            {
                'Name': 'tag-key',
                'Values': ['EbsVolumeBackupLevel']
            }
        ]
        
        while True:
            response = ec2_client.describe_instances(**params)
            for res in response['Reservations']:
                for inst in res['Instances']:
                    inst_json = {}
                    inst_json['InstanceId'] = inst['InstanceId']
                    inst_json['VolumeIds'] = [vol['Ebs']['VolumeId'] for vol in inst['BlockDeviceMappings']]
                    inst_json['LatestBackup'] = ''
                    inst_json['IncidentPriority'] = priority
                    inst_json['Event'] = 'BackupFailure'
                    inst_json['EventDate'] = str(date_time)
                    inst_json['region'] = inst['Placement']['AvailabilityZone'][:-1]
                    
                    for tag in inst['Tags']:
                        if(tag['Key']=='BackupSchedule' and tag['Value'] in ['', None, 'Default','NoValue']):
                            inst_json['LastSchedule'] = rules['Default']
                        elif(tag['Key']=='BackupSchedule' and tag['Value'] not in ['', None, 'Default']):
                            inst_json['LastSchedule'] = rules['Snapshot-Schedule-'+tag['Value']]
                        if(tag['Key']=='EbsVolumeBackupLevel' and tag['Value'] > '0'):
                            instances_lst.append(inst_json)                                                            
                    
            if('NextToken' in response):
                params['NextToken'] = response['NextToken']
            else:
                break
        
        return instances_lst
        
    except Exception as e:
        print('Error describe_instances() -',e)
        raise


def handler(event, context):
    try:
        priority = get_ssm_param_value(ssm_param_backups_inci_priority)
        rules = list_rules()

        for rule in rules:
            cron = rules[rule].replace('cron(','').replace(')','')
            last_sch_time = get_last_sch_time(cron)
            rules[rule] = last_sch_time
        
        instance_list = describe_instances(rules, priority)

        print('Instances sent for Backup Health check - ', instance_list)

        # timelapse = 1
        for inst in instance_list:
            send_msg_to_queue(queueUrl, inst)
            time.sleep(0.125)
            # timelapse += 1

        pass
        return "Lambda executed SUCCESSFULLY"
    except Exception as e:
        print('Lambda Execution error',str(e))


if __name__ == '__main__':
    handler('', '')