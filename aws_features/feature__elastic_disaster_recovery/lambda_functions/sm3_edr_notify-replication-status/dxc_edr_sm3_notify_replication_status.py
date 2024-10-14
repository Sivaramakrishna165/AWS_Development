'''
Implemented through [AWSPE - 6701]

# The sm3 lambda gets the trigger from upon successful completion of sm2 or if any sm gets failed
# Based on the received event, The lambda will construct a json payload and  perform sns publish to notify the status through email.
# The instance tag value will be updated accordingly

Success event:

{
    'InstanceId': '', 
    'RecoveryRegion': ''
}

Failure Event:

{
    'Error':'',
    'Cause':''
}

    Author : Arunkumar Chandrasekar
    CreationDate : 19 Jun 2023
    ModifiedDate : 19 Jun 2023

'''
import json
import os
import boto3
from botocore.config import Config

from recovery_helper import recovery_boto_helper
from primary_helper import primary_boto_helper

primary_boto_obj = primary_boto_helper()
recovery_boto_obj = recovery_boto_helper()

instance_info_table = os.environ['EDRInstanceInfoTable']
topic_arn = os.environ['NotifyEmailTopic']
region = os.environ['Stack_Region']
acc_id = os.environ['Execution_Account']

def lambda_handler(event, context):
    
    try:
        print("Event Received - ", event)

        if('Error' in event):
            try:
                error_json = json.loads(event['Error'])
            except Exception as e:
                print('Not Valid Json Format', str(e))
                error_json = event['Error']
                
            instance_id = error_json['InstanceId']
            recovery_region = error_json['RecoveryRegion']
            
            config=Config(retries=dict(max_attempts=10,mode='standard'))
            recovery_region_ddb_resource = boto3.resource('dynamodb',region_name=recovery_region,config=config)
            recovery_region_drs_client = boto3.client('drs',region_name=recovery_region,config=config)            
                
            item = recovery_boto_obj.get_instance_info(recovery_region_ddb_resource, instance_info_table, instance_id)
            print('DDB Item -', item)
            item['Status'] = event['Cause']
            tag_value = 'Failed'
                
        if('TaskToken' in event):
            instance_id = event['InstanceId']
            recovery_region = event['RecoveryRegion']
            
            config=Config(retries=dict(max_attempts=10,mode='standard'))
            recovery_region_ddb_resource = boto3.resource('dynamodb',region_name=recovery_region,config=config)
            recovery_region_drs_client = boto3.client('drs',region_name=recovery_region,config=config)  
            
            item = recovery_boto_obj.get_instance_info(recovery_region_ddb_resource, instance_info_table, instance_id)
            print('DDB Item -', item)            
            
            source_server_id = item['SourceServerId']
            replication_status = recovery_boto_obj.get_replication_status(recovery_region_drs_client, source_server_id)
            item['Status'] = 'The current replication status is - {}'.format(replication_status)
            tag_value = 'Activated'
            
        print('STATUS -', item)
        
        primary_boto_obj.update_tag(instance_id, 'edr', tag_value)
        text="Find the Elastic Disaster Recovery replication report below:\n\n"
        subject = 'Elastic Disaster Recovery - Replication status Report' + ' Account ' + str(acc_id) + ' Region ' + region
        primary_boto_obj.publish_msg(topic_arn,text,item,subject)
        
    
    except Exception as e:
        print('ERROR -', e)
        raise