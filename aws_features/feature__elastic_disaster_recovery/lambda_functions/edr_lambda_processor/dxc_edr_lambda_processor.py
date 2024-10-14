'''
Implemented through [AWSPE - 6701]

# The trigger event is based on the create/update of the tag "edr" to true/True/TRUE on the instances
# Once the event is received, The processor will validates the event and parameter values. 
# A json item will be created and loaded to the instance info table
# Once successfully loaded, the instance tag will be updated and the step function will be invoked

sample event:

{
   "resources" : "",
   "region" : ""
   
}

    Author : Arunkumar Chandrasekar
    CreationDate : 07 Jun 2023
    ModifiedDate : 07 Jun 2023

'''

import os
import json
import boto3
from botocore.config import Config
import time

from recovery_helper import recovery_boto_helper
from primary_helper import primary_boto_helper

primary_boto_obj = primary_boto_helper()
recovery_boto_obj = recovery_boto_helper()

instance_info_table = os.environ['EDRInstanceInfoTable']
primary_region = os.environ['PrimaryRegionName']
recovery_region = os.environ['RecoveryRegionName']
state_fun_arn = os.environ['StateFunArn']

def lambda_handler(event, context):
    
    try:
        
        print('Event Received - ', event)
    
        instance_id = event['resources'][0].split("/")[1]
        instance_region = event['region']
        
        print('The instance id is {}'.format(instance_id))
        
        inst_status_check = primary_boto_obj.instance_status_check(instance_id)
        
        config=Config(retries=dict(max_attempts=10,mode='standard'))
        recovery_region_ddb_resource = boto3.resource('dynamodb', region_name=recovery_region, config=config)
        
        time.sleep(10)
        osname =  primary_boto_obj.get_instance_osname(instance_id)
        print('The os name is {}'.format(osname))
        
        
        if 'linux' in osname.lower():
            osarch = primary_boto_obj.get_instance_os_arch(instance_id)
            print('The instance os architecture type is {}'.format(osarch))
            
            if osarch.lower() == 'x86_64':
                print('The linux architecture is valid')
            else:
                print('ERROR - The linux architecture is not valid. Hence aborting the process')
                raise Exception('The linux architecture is not valid. Hence aborting the process') 
                
        if instance_region == primary_region:
            instance_info_json = {
                'InstanceId': instance_id,
                'OSName' : osname,
                'PrimaryRegion' : primary_region,
                'RecoveryRegion' : recovery_region
            }
            
            add_instance_info_item = recovery_boto_obj.add_instance_info_item(instance_info_table, instance_info_json, recovery_region_ddb_resource)
        
            primary_boto_obj.update_tag(instance_id, 'edr', 'In Progress')
        
            if add_instance_info_item:
                input = {}
                input['InstanceId'] = instance_id
                input['OSName'] = osname
                input['RecoveryRegion'] = recovery_region
                state_machine_input = json.dumps(input)
                print("calling the statemachine")
                primary_boto_obj.call_state_machine(state_machine_input, state_fun_arn)
            else:
                primary_boto_obj.update_tag(instance_id, 'edr', 'Failed')
        
        else:
            print('ERROR - The region combination is not valid. Hence aborting the process')
            primary_boto_obj.update_tag(instance_id, 'edr', 'Failed')
        
                
    except Exception as e:
        print('ERROR - ', str(e))
        primary_boto_obj.update_tag(instance_id, 'edr', 'Failed')
        raise