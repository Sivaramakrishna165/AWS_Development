'''
Implemented via [AWSPE - 6702]

# This is a custom lambda gets a trigger via cloudformation stack.
# It performs the recovery region setup for replication by: creating vpc peering, updating routes in the route tables in both primary and recovery, creating default edr roles, 
initiating EDR in recovery region and updating the replication config.
# Once the process completed successfully, a status response will be sent back to the stack.

sample event:

{
  "RequestType": "",
  "ServiceToken": "",
  "ResponseURL": "",
  "StackId": "",
  "RequestId": "",
  "LogicalResourceId": "",
  "PhysicalResourceId": "",
  "ResourceType": "",
  "ResourceProperties": {
    "ServiceToken": ""
  }
}


    Author : Arunkumar Chandrasekar
    CreationDate : 03 July 2023
    ModifiedDate : 03 July 2023

'''

import json
import boto3
import os
import time
from botocore.config import Config

from primary_helper import primary_boto_helper
from recovery_helper import recovery_boto_helper

primary_boto_obj = primary_boto_helper()
recovery_boto_obj = recovery_boto_helper()

primary_region = os.environ['PrimaryRegionName']
recovery_region = os.environ['RecoveryRegionName']
account_id = os.environ['AccountId']
edr_replication_vpc_id = os.environ['EDRVPC']
edr_replication_subnet_id = os.environ['EDRSubnet']
edr_replication_s3_endpoint = os.environ['EDRS3Endpoint'] 
edr_replication_route_table = os.environ['EDRRouteTable']
edr_replication_vpc_cidr = os.environ['ReplicationVpcCidr']
region_info_table = os.environ['EDRRegionInfoTable']
afd_table_name = 'AccountFeatureDefinitions'
feature_name = 'ElasticDisasterRecovery'

#Load the default EDR IAM roles
f = open('default_edr_iam_roles.json') 
edr_roles = json.load(f)

def lambda_handler(event, context):
    
    try:
        print('event received-', event)
        response = {}
        response['Status'] = 'SUCCESS'
        response['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
        response['PhysicalResourceId'] = context.log_stream_name
        response['StackId'] = event['StackId']
        response['RequestId'] = event['RequestId']
        response['LogicalResourceId'] = event['LogicalResourceId']
        response['NoEcho'] = False
        
        if (event['RequestType'] in ['Create','Update']) and ('ServiceToken' in event):
            print('CREATE/UPDATE EVENT RECEIVED')

            config=Config(retries=dict(max_attempts=10,mode='standard'))
            primary_region_ec2_client = boto3.client('ec2', region_name=primary_region, config=config)
            
            item=recovery_boto_obj.get_db_items(afd_table_name, feature_name)
            
            edr_replication_instance_type = item['pReplicationInstanceType']['Default']
            edr_replication_pit_retention_in_days = item['pReplicationPitRetentionInDays']['Default']
            primary_server_vpc_id = item['pPrimaryServerVpcId']['Default']
            primary_server_subnet_id = item['pPrimaryServerSubnetId']['Default']
            
            if primary_server_vpc_id:
                print('User provided the primary vpc id')
            else:
                print('Fetching the default vpc id from the primary region')
                primary_server_vpc_id = primary_boto_obj.get_primary_vpc_id(primary_region_ec2_client)
                
            print('The primary vpc id is {}'.format(primary_server_vpc_id))
            
            if primary_server_subnet_id:
                print('User provided the primary subnet id')
            else:
                print('Fetching the default subnet ids from the primary region')
                primary_server_subnet_id = primary_boto_obj.get_primary_subnet_id(primary_region_ec2_client, primary_server_vpc_id)
                
            print('The primary subnet id is {}'.format(primary_server_subnet_id))
        
            #Update s3 endpoint
            endpoint_response = recovery_boto_obj.modify_s3_endpoint(edr_replication_s3_endpoint, edr_replication_route_table)
            
            #Creating vpc peering
            peering_connection_id = recovery_boto_obj.create_vpc_peering(account_id, primary_server_vpc_id, edr_replication_vpc_id, primary_region)
            time.sleep(15)
            
            peering_acceptance_response = primary_boto_obj.accept_peering_connection(primary_region_ec2_client, peering_connection_id)
            
            #Updating replication route table 
            primary_vpc_info = primary_boto_obj.get_vpc_info(primary_region_ec2_client, primary_server_vpc_id)
            cidrs = []
            cidr_list = primary_vpc_info['Vpcs'][0]['CidrBlockAssociationSet']
            for cidr in cidr_list:
                cidrs.append(cidr['CidrBlock'])
            print('The primary vpc cidr is {}'.format(cidrs))
            
            for cidr in cidrs:
                recovery_boto_obj.modify_route_table(cidr, edr_replication_route_table, peering_connection_id)
            print('Replication Route table modification has been completed')
            
            #Updating primary route table
            primary_server_route_table_list = primary_boto_obj.get_route_tables(primary_region_ec2_client, primary_server_vpc_id)
            print(primary_server_route_table_list)
            
            primary_rtb = []
            for rtb in primary_server_route_table_list:
                for rtbasc in rtb['Associations']:
                    if 'SubnetId' in rtbasc:
                        if rtbasc['SubnetId'] in primary_server_subnet_id:
                            primary_rtb.append(rtbasc['RouteTableId'])
            
            for rtb in primary_rtb:
                primary_boto_obj.modify_route_table(primary_region_ec2_client, edr_replication_vpc_cidr, rtb, peering_connection_id)
            print('Primary Route table modification has been completed')    
                            
                            
            #Creating default edr roles
            for key,value in edr_roles.items():
                role_exists = recovery_boto_obj.check_role_exists(key)
                if role_exists:
                    print('The role {} is already exists'.format(key))
                else:
                    print('The role {} is not exists. Hence creating the same'.format(key))
                    recovery_boto_obj.create_iam_role(key,value,account_id)
                    time.sleep(10)
                    
                    if key == 'AWSElasticDisasterRecoveryRecoveryInstanceWithLaunchActionsRole':
                        policy_list = ['arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore','arn:aws:iam::aws:policy/service-role/AWSElasticDisasterRecoveryRecoveryInstancePolicy']
                        for policy_arn in policy_list:
                            recovery_boto_obj.attach_policy(key,policy_arn)
                    else:
                        policy_name = key.replace('Role','Policy')
                        policy_arn = 'arn:aws:iam::aws:policy/service-role/'+policy_name
                        print('Policy ARN -', policy_arn) ## DELETE
                        recovery_boto_obj.attach_policy(key,policy_arn)
            
            #EDR Initiation        
            initiate_edr = recovery_boto_obj.initiate_edr()      
            time.sleep(15)

            #Default Replication Configuration
            replication_config_response = recovery_boto_obj.get_replication_config_temp()
            if replication_config_response:
                rep_config_tempid = replication_config_response[0]['replicationConfigurationTemplateID']
                print('The template id is {}'.format(rep_config_tempid))
                print('The default replication configuration template is alreay available. Updating the same.')
                recovery_boto_obj.update_rep_config_temp(rep_config_tempid, edr_replication_instance_type, edr_replication_subnet_id, edr_replication_pit_retention_in_days)
            else:
                print('The default replication configuration template is not available. Creating the same.')
                recovery_boto_obj.create_rep_config_temp(edr_replication_instance_type, edr_replication_subnet_id, edr_replication_pit_retention_in_days)
            
            region_info_json = {
                'PrimaryRegionName': primary_region,
                'RecoveryRegionName': recovery_region,
                'ReplicationVPC': edr_replication_vpc_id,
                'PrimaryVPC': primary_server_vpc_id,
                'PeeringConnectionId': peering_connection_id
            }
            add_region_info_item_response = recovery_boto_obj.add_region_info_item(region_info_table, region_info_json)
                
            recovery_boto_obj.send_response(event, response, status='SUCCESS', reason='Lambda Completed')
            
        if (event['RequestType'] in ['Delete']) and ('ServiceToken' in event):
            print('DELETE EVENT RECEIVED. Nothing to do.')
            
            recovery_boto_obj.send_response(event, response, status='SUCCESS', reason='Delete event recevied. Nothing done.')
            
    except Exception as e:
        print('ERROR -', str(e))
        recovery_boto_obj.send_response(event, response, status='FAILED', reason=str(e))