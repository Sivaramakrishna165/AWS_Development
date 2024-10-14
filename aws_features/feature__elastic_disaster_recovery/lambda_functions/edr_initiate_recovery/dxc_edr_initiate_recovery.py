'''
Implemented via [AWSPE - 6702]

#The lambda receives the event from an event rule that looks for any ec2 health related tickets from the health dashboard.
#Once the event received, the lambda do the region verification and fetch the instance that are part of the affected region from the dynamodb table.
#The tags on the instances will be verified and the recovery will be initiated for the intances that are valid.

sample event:
{
    {
  "region": "",
  "resources": [
    ""
  ],

}
}


    Author : Arunkumar Chandrasekar
    CreationDate : 06 July 2023
    ModifiedDate : 06 July 2023

'''

import json
import boto3
import os
from botocore.config import Config
from primary_helper import primary_boto_helper
from recovery_helper import recovery_boto_helper

primary_boto_obj = primary_boto_helper()
recovery_boto_obj = recovery_boto_helper()

primary_region = os.environ['PrimaryRegionName']
recovery_region = os.environ['RecoveryRegionName']
instance_info_table = os.environ['EDRInstanceInfoTable']
region = os.environ['Stack_Region']
acc_id = os.environ['Execution_Account']
topic_arn = os.environ['NotifyEmailTopic']

def lambda_handler(event, context):
    
    try:
        print("Event Received - ", event)
        event_region = event['region']
        affected_resources = event['resources']
        
        print('Primary Region -',primary_region)
        print('Region in source event -',event_region)
        print('The affected resources are',affected_resources)
    
        config=Config(retries=dict(max_attempts=10,mode='standard'))
        primary_region_ec2_client = boto3.client('ec2', region_name=primary_region, config=config)        
        
        if primary_region == event_region:
            print('The primary region and the region from the source event are MATCHING')
        else:
            print('The primary region and the region from the source event are NOT MATCHING')
            raise Exception('The primary region and the region from the source event are NOT MATCHING')
        
        #get the list of instance from the instance info table that are part of the mentioned primary region
        instance_list = recovery_boto_obj.get_instance_info(instance_info_table, primary_region)
        print('The instances that are part of the primary region {} are {}'.format(primary_region,instance_list))
        
        #Fetching the instance that needs to be recovered
        instance_to_be_recovered = []
        for instance in instance_list:
            if instance in affected_resources:
                instance_to_be_recovered.append(instance)
        print('The instances that are needed to be recovered - ',instance_to_be_recovered)
        
        item = {}
        if instance_to_be_recovered:
            for instance in instance_to_be_recovered:
                #check the edr tag is activated
                instance_edr_tag_status = primary_boto_obj.verify_instance_tag(primary_region_ec2_client, instance)
                if instance_edr_tag_status:
                    print('The edr tag value is ACTIVATED for the instance -',instance)
                    source_server_id = recovery_boto_obj.get_db_item(instance, instance_info_table)
                    print('The source server id of the instance {} is - {}'.format(instance, source_server_id))
                    if source_server_id:
                        recovery_response = recovery_boto_obj.initiate_recovery(source_server_id)
                        print('Initiated Recovery for the instance - ',instance)
                        
                        item['PrimaryRegion'] = primary_region
                        item['RecoveryRegion'] = recovery_region
                        item['InstanceId'] = instance
                        item['JobDetail'] = recovery_response['job']
                        item['Comment'] = 'Monitor the recovery job'
                        
                        primary_boto_obj.update_tag(primary_region_ec2_client, instance, 'edr', 'RecoveryInitiated')
                        text="Find the Elastic Disaster Recovery Report below:\n\n"
                        subject = 'Elastic Disaster Recovery - Recovery status Report' + ' Account ' + str(acc_id) + ' Region ' + region
                        recovery_boto_obj.publish_msg(topic_arn,text,item,subject)
                        
                    else:
                        print('Source server id for the instance {} is not found. Hence recovery is NOT initiated'.format(instance))
                else:
                    print('The edr tag value is not ACTIVATED for the instance - ',instance)
                    
        else:
            print('There are no instances to be recovered. Hence ending the process.')
        
       
        
    except Exception as e:
        print('ERROR -',str(e))
        raise e