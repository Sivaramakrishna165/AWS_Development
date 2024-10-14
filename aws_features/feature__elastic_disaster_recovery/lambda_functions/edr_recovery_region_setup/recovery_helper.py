'''
Boto Helper class contain all the supported aws api operations
'''

import boto3
from botocore.config import Config
import json
import urllib.parse
import http.client

class recovery_boto_helper():
    
    def __init__(self):
        self.config = Config(retries=dict(max_attempts=10,mode='standard'))
        self.ec2_client = boto3.client('ec2', config = self.config)
        self.iam_client = boto3.client('iam', config = self.config)
        self.drs_client = boto3.client('drs', config = self.config)
        self.ddb_resource = boto3.resource('dynamodb', config = self.config)
        
    #To send the response back to cfn template
    def send_response(self, request, response, status=None, reason=None):
        if status is not None:
            response['Status'] = status
        if reason is not None:
            response['Reason'] = reason
        if 'ResponseURL' in request and request['ResponseURL']:
            try:
                url = urllib.parse.urlparse(request['ResponseURL'])
                body = json.dumps(response)
                https = http.client.HTTPSConnection(url.hostname)
                https.request('PUT', url.path + '?' + url.query, body)
                print('Response sent successfully')
            except Exception as e:
                print('ERROR -',str(e))
                print("Failed to send the response to the provided URL")
        return response        
        
    #To fetch the item from the AFD table
    def get_db_items(self, table_name, feature_name):
        
        try:
            table = self.ddb_resource.Table(table_name)
            
            response = table.get_item(Key={"Feature":feature_name})
            print('Item successfully fetched from the AFD table')
            return response['Item']['FeatureParams']
        
        except Exception as e:
            print('ERROR - ', str(e))
            raise
    
    #To add the route tables to the s3 endpoint
    def modify_s3_endpoint(self, endpoint_id, route_table):
        
        try:
            response = self.ec2_client.modify_vpc_endpoint(
                VpcEndpointId=endpoint_id,
                AddRouteTableIds=[route_table]
                )
            print('Endpoint response', response)
            print('The endpoint {} has been modified successfully'.format(endpoint_id))
        
        except Exception as e:
            print('ERROR -', str(e))
            raise e
            
    #To create vpc peering connection
    def create_vpc_peering(self, account_id, primary_server_vpc_id, edr_replication_vpc_id, recovery_region):
        
        try:
            response = self.ec2_client.create_vpc_peering_connection(
                PeerOwnerId = account_id,
                PeerVpcId = primary_server_vpc_id,
                VpcId = edr_replication_vpc_id,
                PeerRegion = recovery_region
                )
            print('Peering Response -', response)
            peering_connection_id = response['VpcPeeringConnection']['VpcPeeringConnectionId']
            print('The peering connection id is', peering_connection_id)
            peering_connection_status = response['VpcPeeringConnection']['Status']['Code']
            print('The peering connection status is', peering_connection_status)
            
            return peering_connection_id
                
        except Exception as e:
            print('ERROR -', str(e))
            raise e
            
    #To add the route to the route table
    def modify_route_table(self, cidr, routetable, peering_connection_id):
        
        try:
            response = self.ec2_client.create_route(
                DestinationCidrBlock=cidr,
                RouteTableId=routetable,
                VpcPeeringConnectionId=peering_connection_id
                )
        
        except Exception as e:
            print(str(e))
        
        finally:
            response = self.ec2_client.replace_route(
                DestinationCidrBlock=cidr,
                RouteTableId=routetable,
                VpcPeeringConnectionId=peering_connection_id
                )
            
    #To check whether the role is exists or not
    def check_role_exists(self, role):
        
        try:
            response = self.iam_client.get_role(
                RoleName=role
            )
            return True
            
        except Exception as e:
            return False
    
    #To create IAM role
    def create_iam_role(self, role_name, policy, account_id):
        
        try:
            trust_policy = policy
            print(trust_policy) ## DELETE
            if 'Condition' in trust_policy['Statement'][0]:
                trust_policy['Statement'][0]['Condition']['StringLike']['aws:SourceAccount'] = account_id
            print(trust_policy) ## DELETE
            
            response = self.iam_client.create_role(
                Path='/service-role/',
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy)
                )
            print('Create role response -', response)
            print('The role {} has been created successfully'.format(role_name))
            
        except Exception as e:
            print('ERROR -', str(e))
            raise e
            
    #To attach the policy to the created role
    def attach_policy(self, role_name, policy_arn):
        
        try:
            response = self.iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
                )
            print('The policy has been successfully attached to the role {}'.format(role_name))
            
        except Exception as e:
            print('ERROR -', str(e))
            raise e
            
    #To initiate the edr service
    def initiate_edr(self):
        
        try:
            response = self.drs_client.initialize_service()
            print('EDR initiated')
        
        except Exception as e:
            raise e
    
    #To get the default replication configuration info
    def get_replication_config_temp(self):
        
        try:
            response = self.drs_client.describe_replication_configuration_templates(
                replicationConfigurationTemplateIDs=[]
                )
            
            return response['items']
            
        except Exception as e:
            print('ERROR -', str(e))
            raise e
            
    #To update the default replication config template
    def update_rep_config_temp(self, temp_id, inst_type, subnet_id, retention_days):
        
        try:
            response = self.drs_client.update_replication_configuration_template(
                associateDefaultSecurityGroup=True,
                autoReplicateNewDisks=True,
                bandwidthThrottling=0,
                createPublicIP=False,
                dataPlaneRouting='PRIVATE_IP',
                defaultLargeStagingDiskType='AUTO',
                ebsEncryption='DEFAULT',
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
                replicationConfigurationTemplateID= temp_id,
                replicationServerInstanceType= inst_type,
                stagingAreaSubnetId= subnet_id,
                useDedicatedReplicationServer=True,
                stagingAreaTags={
                    'EDR': 'Replication Resource'
                }                
            )
            print('The default replication configuration template has been updated successfully')
        
        except Exception as e:
            print('ERROR -', str(e))
            raise e
            
    #To create the default replication config template
    def create_rep_config_temp(self, inst_type, subnet_id, retention_days):
        
        try:
            response = self.drs_client.create_replication_configuration_template(
                associateDefaultSecurityGroup=True,
                autoReplicateNewDisks=True,
                bandwidthThrottling=0,
                createPublicIP=False,
                dataPlaneRouting='PRIVATE_IP',
                defaultLargeStagingDiskType='AUTO',
                ebsEncryption='DEFAULT',
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
                replicationServerInstanceType=inst_type,
                stagingAreaSubnetId=subnet_id,
                useDedicatedReplicationServer=True,
                replicationServersSecurityGroupsIDs=[],
                stagingAreaTags={
                    'EDR': 'Replication Resource'
                }
            )
            print('The default replication configuration template has been created successfully')
            
        except Exception as e:
            print('ERROR -', str(e))
            raise e
        
    #To add the item to the dynamodb table    
    def add_region_info_item(self, tbl_name, item_json):
        
        try:
            table = self.ddb_resource.Table(tbl_name)
            table.put_item(Item=item_json)
            print("Item added to the table-",tbl_name)
        
        except Exception as e:
            print("ERROR adding item: {}  - {}".format(item_json, str(e)))
            raise