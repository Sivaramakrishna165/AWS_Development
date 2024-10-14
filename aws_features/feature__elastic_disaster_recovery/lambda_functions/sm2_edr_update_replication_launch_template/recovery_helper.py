'''
Boto Helper class contain all the supported aws api operations
'''

import boto3

class recovery_boto_helper():
    
    #To fetch the item from the AFD table
    def get_db_items(self, ddb_resource, table_name, feature_name):
        
        try:
            table = ddb_resource.Table(table_name)
            
            response = table.get_item(Key={"Feature":feature_name})
            print('Item successfully fetched from the AFD table')
            return response['Item']['FeatureParams']
        
        except Exception as e:
            print('ERROR - ', str(e))
            raise

    #To convert the string value to boolean
    def str_to_bool(self,recovery_copy_private_ip):
        if recovery_copy_private_ip.lower() == 'true':
            return True
        elif recovery_copy_private_ip.lower() == 'false':
            return False
        else:
            raise ValueError
            
    #To get the recovery subnet id
    def get_recovery_subnet_id(self, ec2_client):
        
        try:
            response = ec2_client.describe_subnets()
            subnet_lst = response['Subnets']
            
            for subnet in subnet_lst:
                for tags in subnet['Tags']:
                    if tags['Key'] == 'Name' and tags['Value'] == 'Private Workload A':
                        subnet_id = subnet['SubnetId']
            return subnet_id
        
        except Exception as e:
            print('ERROR -', str(e))
            raise e
    
    #To fetch the ssm parameter value
    def get_ssm_parameter(self, ssm_client, ssm_param):
        
        try:
            response = ssm_client.get_parameter(
                Name=ssm_param
            )
            print('Successfully fetched the value from the ssm parameter for {}'.format(ssm_param))
            return response['Parameter']['Value']
        
        except Exception as e:
            print('ERROR -', str(e))
    
    #To fetch the source server id using the instance id        
    def get_source_server_id(self,drs_client, instance_id):
        
        try:
            response = drs_client.describe_source_servers(
                filters={
                    'hardwareId': instance_id
                }
                )
            
            source_server_id = response['items'][0]['sourceServerID']
            return source_server_id
            
        except Exception as e:
            print('ERROR - ', str(e))
            raise
    
    #To update the recovery launch configuration    
    def update_launch_config(self, drs_client, source_server_id, copy_private_ip, launch_disposition, instance_type_right_sizing):
        
        try:
            response = drs_client.update_launch_configuration(
                sourceServerID= source_server_id,
                copyPrivateIp= copy_private_ip,
                copyTags= False,
                launchDisposition= launch_disposition,
                licensing={
                    'osByol': False
                },
                targetInstanceTypeRightSizingMethod= instance_type_right_sizing
                )
            
            print('Successfully updated the launch configuration for the source server {}'.format(source_server_id))
            
        except Exception as e:
            print('ERROR - ', str(e))
            raise
    
    #To fetch the recovery launch template id   
    def get_launch_temp_id(self, drs_client, source_server_id):
        
        try:
            response = drs_client.get_launch_configuration(
                sourceServerID= source_server_id
                )
            
            launch_temp_id = response['ec2LaunchTemplateID']
            return launch_temp_id
            
        except Exception as e:
            print('ERROR - ', str(e))
            raise
        
    #To fetch the latest launch template version            
    def get_launch_temp_version(self, ec2_client, launch_temp_id):
        
        try:
            response = ec2_client.describe_launch_templates(
                LaunchTemplateIds = [launch_temp_id]
                )
            
            return response
            
        except Exception as e:
            print('ERROR - ', str(e))
            raise
        
    #To get the details of a particular template version
    def get_launch_temp_detail(self, ec2_client, launch_temp_id, default_temp_version):
        
        try:
            response = ec2_client.describe_launch_template_versions(
                LaunchTemplateId= launch_temp_id,
                Versions=[default_temp_version]
                )
            return response
        
        except Exception as e:
            print('ERROR -', str(e))
            raise
    
    #To update the recovery launch template     
    def update_launch_template(self, ec2_client, launch_temp_id, recovery_instance_type, recovery_sg, recovery_subnet_id, recovery_key_pair, recovery_instance_profile, block_device, tags):
        
        try:
            response = ec2_client.create_launch_template_version(
                LaunchTemplateId = launch_temp_id,
                LaunchTemplateData={
                    'InstanceType': recovery_instance_type,
                    'NetworkInterfaces': [
                        {
                         'DeviceIndex': 0,      
                         'SubnetId': recovery_subnet_id,
                         'Groups': [recovery_sg]   
                        }
                        ],
                    'KeyName': recovery_key_pair,
                    'IamInstanceProfile' : {'Name': recovery_instance_profile},
                    'BlockDeviceMappings' : block_device,
                    'TagSpecifications' : tags
                }
            
                )
            print('Updated the launch template successfully')
        
        except Exception as e:
            print('ERROR - ', str(e))
            raise
    
    #To update the launch template version to the latest    
    def update_launch_temp_version(self, ec2_client, launch_temp_id, latest_temp_version):
        
        try:
            response = ec2_client.modify_launch_template(
                LaunchTemplateId = launch_temp_id,
                DefaultVersion = latest_temp_version
                )
            print('The launch template version is successfully updated to {}'.format(latest_temp_version))    
            
        except Exception as e:
            print('ERROR - ', str(e))
            raise
        
    #To update the item in dynamodb table
    def update_ddb_item(self, ddb_resource, instance_info_table, instance_id, source_server_id, launch_temp_id):
        
        try:
            table = ddb_resource.Table(instance_info_table)
            response = table.update_item(
                Key = {
                    'InstanceId': instance_id
                },
                UpdateExpression='SET SourceServerId=:sourceserverid, LaunchTempId=:launchtempid', 
                ExpressionAttributeValues={
                    ':sourceserverid':source_server_id,
                    ':launchtempid':launch_temp_id
                }
            )
            
        except Exception as e:
            print('ERROR -', str(e))
            raise
        
    #To update the replication config for the individual server using the source server id
    def update_replication_config(self, drs_client, source_server_id, instance_type, retention_days):
        
        try:
            response = drs_client.update_replication_configuration(
                sourceServerID= source_server_id,
                replicationServerInstanceType= instance_type,
                pitPolicy=[
                    {
                        'enabled': True,
                        'interval': 10,
                        'retentionDuration': 60,
                        'ruleID': 1,
                        'units': 'MINUTE'
                    },
                    {
                        'enabled': True,
                        'interval': 1,
                        'retentionDuration': 24,
                        'ruleID': 2,
                        'units': 'HOUR'
                    },
                    {
                        'enabled': True,
                        'interval': 1,
                        'retentionDuration': int(retention_days),
                        'ruleID': 3,
                        'units': 'DAY'
                    },        
                ],                
            )
        
        except Exception as e:
            print('ERROR -',str(e))
            raise e