'''
    Lambda functions checks for recent Backups/snapshot for the volumes.
    This lambda function is invoked by QUEUE - dxc-ebsbackup-health-queue
    The message holds event/message required for the function to execute.

    If the snapshot is available then a message is logged in 
        BackupLogGroup = 'BackupLogGroup'
        BackupMessageStream = 'BackupMessageStream'
    
    In case of snapshot is not available then, message is publshed to snsTopic 'BackupSNSTopic' and same is logged in
        BackupLogGroup = 'BackupLogGroup'
        BackupMessageStream = 'BackupMessageStream'

Created By - Kedarnath Potnuru
Date - 18 July 2023
'''

import boto3
import time
import os
import json
from datetime import datetime
from botocore.config import Config

config = Config(retries=dict(max_attempts=10,mode='standard'))
ec2_client = boto3.client('ec2', config=config)
sqs_client = boto3.client('sqs', config=config)
sns_client = boto3.client('sns', config=config)
log_client = boto3.client('logs', config=config)

BackupSNSTopic = 'BackupSNSTopic'
BackupLogGroup = 'BackupLogGroup'
BackupMessageStream = 'BackupMessageStream'

queueUrl = os.environ['QueueUrl']
topicArn= ''

def del_msg_from_queue(queueUrl, receiptHandle):
    try:
        sqs_client.delete_message(
                QueueUrl=queueUrl,
                ReceiptHandle=receiptHandle
            )
    except Exception as e:
        print('Error del_msg_from_queue()-',e)

def send_message(message, instance_info_json, topicArn,  account, region):
    try:
        subject = 'AWSMS Backup Health ERROR - '+ 'Account: '+account+ ', Region: '+region
        
        text = 'The Backup Health Service encountered the following: \n' + message + '\n\n'
      
        text += 'Payload information:\n'
        text += '-------------------------------\n'
        text += json.dumps(instance_info_json, indent=4)
        text += '\n\n'

        text += 'NOTE: Payload sent to SelfHeal for Backup retry.'
        
        text += '\n\n'

        snsJson= {}
        snsJson['default'] = json.dumps(instance_info_json)
        snsJson['email'] = text
        snsJson['https'] = json.dumps(instance_info_json)
        
        snsJsonMsg = json.dumps(snsJson)
        
        snsParams = {
            'MessageStructure': 'json',
            'Message': snsJsonMsg,
            'Subject': subject,
            'TopicArn': topicArn
        }
        
        sns_client.publish(**snsParams)
        
    except Exception as e:
        print('Error send_message()',e)        


#To load the logs into log stream
def put_log(log_group, log_stream, message):
    try:

        response = log_client.put_log_events(
            logGroupName=log_group,
            logStreamName=log_stream,
            logEvents=[
                {
                    'timestamp': int(datetime.utcnow().timestamp() * 1000),
                    'message': json.dumps(message)
                },
            ]
        )
        
    except Exception as e:
        print("Error occured in put_log():",e)


def verify_snapshots_for_volume(instanceId, volumeid, last_schedule_time):
    try:
        bln_snapshot_exists = False
        args = {}
        args['Filters']=[
                  {
                      'Name': 'volume-id',
                      'Values': [volumeid]
                  },
                  {
                    'Name': 'tag:Name',
                    'Values': [ 'InstanceId: {}'.format(instanceId) ]
                },
              ]
        
        while True:
            response = ec2_client.describe_snapshots(**args)
            for snap in response['Snapshots']:
                start_time = time.mktime(snap['StartTime'].timetuple())
                if(start_time >= last_schedule_time):
                    bln_snapshot_exists = True
                    print('Latest Backup/Snapshot AVAILABLE for volume: "{}", snapshotId: "{}" start-time: "{}"'.format(
                                volumeid, snap['SnapshotId'], snap['StartTime']))
                    break                
            if ('NextToken' in response):
                args['NextToken'] = response['NextToken']
            else:
                break
        
        if(not bln_snapshot_exists):
            print('Latest Backup/Snapshot NOT available for volume:', volumeid)
            return False
        
        return True
            
    except Exception as e:
        print('Error - verify_snapshots_for_volume - ',e)
        print('Unable to verify Backup for volume -')

def handler(event, context):
    try:
        print('Event received ', event)
        account = context.invoked_function_arn.split(":")[4]
        region = context.invoked_function_arn.split(":")[3]
        topicArn = 'arn:aws:sns:{}:{}:{}'.format(region, account, BackupSNSTopic)
        for record in event['Records']:
            instance_info_json= {}
            try:
                messageId = record['messageId']
                receiptHandle = record['receiptHandle']
                sns_msg = ''
                if isinstance(record['body'], str):
                    instance_info_json = json.loads(record['body'])
                else:
                    instance_info_json = record['body']
                
                print('EBSBackup Health check processing started for instance: {}, volumes: {}'.format(instance_info_json['InstanceId'], instance_info_json['VolumeIds']))
                
                failed_volumes=[]
                for vol in instance_info_json['VolumeIds']:
                    if(verify_snapshots_for_volume(instance_info_json['InstanceId'], vol, instance_info_json['LastSchedule'])):
                        pass
                    else:
                        failed_volumes.append(vol)
                        
                if (failed_volumes):
                    instance_info_json['VolumeIds'] = failed_volumes
                    sns_msg = 'A Backup for Instance: "{}", volume/volumes: "{}" Failed.'.format(instance_info_json['InstanceId'], failed_volumes)
                    print('Sending event to SelfHeal - ',instance_info_json)
                    
                    send_message(sns_msg, instance_info_json, topicArn, account, region)
                    put_log(BackupLogGroup, BackupMessageStream, instance_info_json)
                else:
                    instance_info_json['Event'] = 'BackupSuccess'
                    put_log(BackupLogGroup, BackupMessageStream, instance_info_json)
                    
                # write code to remove/delete message from Queue
                del_msg_from_queue(queueUrl, receiptHandle)
                print('InstanceId: "{}" processed for BackupHealth check, deleted from sqs queue'.format(instance_info_json['InstanceId']))
                
            except Exception as e:
                print('Issue with EBSBackup Health', str(e))
                print('Sending event to SelfHeal - ',instance_info_json)
        
        print('Details added to logGroupName: {}, logStreamName: {}'.format(BackupLogGroup, BackupMessageStream))
        return "Lambda executed SUCCESSFULLY"
    except Exception as e:
        print('Lambda execution Failed', e)