'''
Implemented via [AWSPE - 6701]

# The lambda(sm2) recevies the trigger from the sm1
# It set up the launch template for the recovery instance in the recovery region
# Once the process completed successfully, a success status will be sent to stepfunction to invoke the next statemachine sm3.

sample event:

{
  "InstanceId": "",
  "RecoveryRegion": "",
  "TaskToken":""
}


    Author : Arunkumar Chandrasekar
    CreationDate : 12 Jun 2023
    ModifiedDate : 12 Jun 2023

'''
import json
import boto3
from botocore.config import Config
import time
import os

from recovery_helper import recovery_boto_helper
from primary_helper import primary_boto_helper

primary_boto_obj = primary_boto_helper()
recovery_boto_obj = recovery_boto_helper()

instance_info_table = os.environ['EDRInstanceInfoTable']
table_name = 'AccountFeatureDefinitions'
feature_name = 'ElasticDisasterRecovery'
recovery_instance_profile_ssm_param = '/DXC/IAMResources/DefaultInstanceProfile'
recovery_sg_ssm_param = '/DXC/Hardening/SecurityGroupId'
recovery_keypair_ssm_param = '/DXC/Hardening/KeyPair'

def lambda_handler(event, context):
    
    print("Event Received - ", event)
    
    instance_id = event['InstanceId']
    recovery_region = event['RecoveryRegion']
    osname = event['OSName']
    taskToken = event['TaskToken']
    
    error = {}
    error['InstanceId'] = instance_id
    error['RecoveryRegion'] = recovery_region

    try:        
        config=Config(retries=dict(max_attempts=10,mode='standard'))
        recovery_region_drs_client = boto3.client('drs', region_name=recovery_region, config=config)
        recovery_region_ec2_client = boto3.client('ec2', region_name=recovery_region, config=config)
        recovery_region_ddb_resource = boto3.resource('dynamodb',region_name=recovery_region,config=config)
        recovery_region_ssm_client = boto3.client('ssm',region_name=recovery_region,config=config)
        
        item=recovery_boto_obj.get_db_items(recovery_region_ddb_resource, table_name, feature_name)
        
        replication_instance_type = item['pReplicationInstanceType']['Default']
        replication_pit_retention_in_days = item['pReplicationPitRetentionInDays']['Default']
        
        recovery_copy_private_ip = item['pRecoveryCopyPrivateIp']['Default']
        bool_recovery_copy_private_ip = recovery_boto_obj.str_to_bool(recovery_copy_private_ip)
        
        recovery_launch_disposition = item['pRecoveryLaunchDisposition']['Default']
        recovery_instance_type_right_sizing = item['pRecoveryTargetInstanceTypeRightSizingMethod']['Default']
        recovery_instance_type = item['pRecoveryInstanceType']['Default']
        
        recovery_subnet_id = item['pRecoverySubnetId']['Default']
        if recovery_subnet_id:
            print('User provided the recovery subnet id - {}'.format(recovery_subnet_id))
        else:
            print('Fetching the default subnet id that is part of workload vpc')
            recovery_subnet_id = recovery_boto_obj.get_recovery_subnet_id(recovery_region_ec2_client)
            print('The recovery subnet id is - {}'.format(recovery_subnet_id))
        
        recovery_sg = item['pRecoverySecurityGroup']['Default']
        if recovery_sg:
            print('User provided the recovery security group - {}'.format(recovery_sg))
        else:
            print('Fetching the default hardening security group that is part of workload vpc')
            recovery_sg = recovery_boto_obj.get_ssm_parameter(recovery_region_ssm_client, recovery_sg_ssm_param)
            print('The recovery security group is - {}'.format(recovery_sg))
            
        recovery_key_pair = item['pRecoveryKeyPair']['Default'] 
        if recovery_key_pair:
            print('User provided the recovery key pair - {}'.format(recovery_key_pair))
        else:
            print('Fetching the default hardening key pair that is part of workload vpc')
            recovery_key_pair = recovery_boto_obj.get_ssm_parameter(recovery_region_ssm_client, recovery_keypair_ssm_param)
            print('The recovery key pair is - {}'.format(recovery_key_pair))
            
        recovery_instance_profile = recovery_boto_obj.get_ssm_parameter(recovery_region_ssm_client, recovery_instance_profile_ssm_param)
        print('The recovery instance profile is - {}'.format(recovery_instance_profile))
        
        source_server_id = recovery_boto_obj.get_source_server_id(recovery_region_drs_client, instance_id)
        print('The source server id is - {}'.format(source_server_id))
        
        launch_temp_id = recovery_boto_obj.get_launch_temp_id(recovery_region_drs_client, source_server_id)
        print('The launch template id is - {}'.format(launch_temp_id))
        
        time.sleep(30)
        get_default_temp_version = recovery_boto_obj.get_launch_temp_version(recovery_region_ec2_client, launch_temp_id)
        default_temp_version = str(get_default_temp_version['LaunchTemplates'][0]['DefaultVersionNumber'])
        print('The default launch template version is {}'.format(default_temp_version))
        
        get_launch_temp_detail = recovery_boto_obj.get_launch_temp_detail(recovery_region_ec2_client, launch_temp_id, default_temp_version)
        if 'BlockDeviceMappings' in get_launch_temp_detail['LaunchTemplateVersions'][0]['LaunchTemplateData']:
            block_device = get_launch_temp_detail['LaunchTemplateVersions'][0]['LaunchTemplateData']['BlockDeviceMappings']
        else:
            block_device = [{}]
        if 'TagSpecifications' in get_launch_temp_detail['LaunchTemplateVersions'][0]['LaunchTemplateData']:
            tags = get_launch_temp_detail['LaunchTemplateVersions'][0]['LaunchTemplateData']['TagSpecifications']
        else:
            tags = [{}]
        
        print('Block Device-', block_device)
        print('Tags -', tags)
        
        print('Update replication configuration for the source instance using the source server id - started')
        update_replication_config = recovery_boto_obj.update_replication_config(recovery_region_drs_client, source_server_id, replication_instance_type, replication_pit_retention_in_days)
        print('Update replication configuration for the source instance using the source server id - completed')
        
        update_launch_config = recovery_boto_obj.update_launch_config(recovery_region_drs_client, source_server_id, bool_recovery_copy_private_ip, recovery_launch_disposition, recovery_instance_type_right_sizing)
        
        time.sleep(30)
        update_launch_temp = recovery_boto_obj.update_launch_template(recovery_region_ec2_client, launch_temp_id, recovery_instance_type, recovery_sg, recovery_subnet_id, recovery_key_pair, recovery_instance_profile, block_device, tags)
        
        get_latest_temp_version = recovery_boto_obj.get_launch_temp_version(recovery_region_ec2_client, launch_temp_id)
        latest_temp_version = str(get_latest_temp_version['LaunchTemplates'][0]['LatestVersionNumber'])
        print('The latest launch template version is {}'.format(latest_temp_version))
        
        update_launch_temp_version = recovery_boto_obj.update_launch_temp_version(recovery_region_ec2_client, launch_temp_id, latest_temp_version)
        
        print('The recovery instance launch template setup is completed successfully for the instance {}'.format(instance_id))
        recovery_boto_obj.update_ddb_item(recovery_region_ddb_resource, instance_info_table, instance_id, source_server_id, launch_temp_id)
        payload_json = {'TaskToken':taskToken, 'InstanceId':instance_id, 'OSName':osname, 'RecoveryRegion':recovery_region, 'Message': 'The recovery instance launch template configuration is completed successfully for the instance {}'.format(instance_id)}
        primary_boto_obj.handle_success(taskToken, payload_json)
    
        
    except Exception as e:
        print('ERROR -', str(e))
        error['Error'] = 'Exception occured while performing launch template setup'
        error['Cause'] = 'The recovery instance launch template setup is failed for the instance {}'.format(instance_id)
        primary_boto_obj.handle_failure(taskToken, error, instance_id)
        raise