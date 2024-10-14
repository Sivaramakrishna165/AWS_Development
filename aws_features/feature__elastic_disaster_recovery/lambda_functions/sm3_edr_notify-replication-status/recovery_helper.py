'''
Boto Helper class contain all the supported aws api operations
'''

import boto3

class recovery_boto_helper():
    
    #To get then instance info from dynamodb table
    def get_instance_info(self, ddb_resource, instance_info_table, instance_id):
        
        try:
            table = ddb_resource.Table(instance_info_table)
            response = table.get_item(
                Key={
                    'InstanceId': instance_id
                }
            )
            
            item = response['Item']
            return item
            
        except Exception as e:
            print('ERROR -', e)
            raise
        
    #To get the replication status
    def get_replication_status(self, drs_client, source_server_id):
        
        try:
            response = drs_client.describe_source_servers(
                filters={
                    'sourceServerIDs': [source_server_id]
                    
                }
                
                )
            
            status = response['items'][0]['dataReplicationInfo']['dataReplicationState']
            return status
        
        except Exception as e:
            print('ERROR -', e)
            raise