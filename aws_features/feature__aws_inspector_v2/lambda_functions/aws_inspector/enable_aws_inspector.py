
import json,os
import boto3

from botocore.config import Config

class enable_aws_inspector:
    
    def __init__(self):
        
        config=Config(retries=dict(max_attempts=10,mode='standard'))
        self.inspector = boto3.client('inspector2',config=config)
        self.ddb_resource = boto3.resource('dynamodb',config=config)
    
    #To get the resource list to enable the inspector
    def get_resource_types(self,table_name,feature_name):
        
        try:
            table = self.ddb_resource.Table(table_name)
            
            response = table.get_item(Key={"Feature":feature_name})
            print('Item successfully fetched from the AFD table')
            return response['Item']['FeatureParams']['pResourceTypes']['Default']
        
        except Exception as e:
            print('ERROR - ', str(e))
            raise    

    # enabling inspector for the specific account
    # inspector is a regional service
    def enable_inspector(self,account_id,resource_list):
        try:

            response = self.inspector.enable(
                        accountIds=[
                            account_id,
                        ],
                        resourceTypes=resource_list
                    )
            print('response:',response)

        except Exception as e:
            print('error in enable_inspector():',e)
            raise

    def handler_impl(self, event, context, resource_list):

        account_id = context.invoked_function_arn.split(':')[4]
        print('account_id:',account_id)

        self.enable_inspector(account_id, resource_list)
