
'''
[AWSPE-6744]
This is a custom lambda function, which creates the ecr replication rule so that ecr repo with images can get replicated to cross-region/cross account destinations.

The event that is passed to this lambda typically looks like this:

{
   "RequestType":"",
   "ServiceToken":"",
   "StackId":"",
   "RequestId":"",
   "LogicalResourceId":""
}
'''

import boto3
import json
import os
from boto_helper import BotoHelper

# Create an instance of BotoHelper
boto_helper = BotoHelper()

# Create an STS and  client
sts_client = boto3.client('sts')
ecr_client = boto3.client('ecr')


def lambda_handler(event, context):
    # Get the parameters from the environment variables
    cross_account_replication = os.getenv('CrossAccountReplication', 'false').lower() == 'true'
    cross_account_destination_account_ids = os.getenv('CrossAccountDestinationAccountIds', '').split(',')
    cross_account_destination_regions = os.getenv('CrossAccountDestinationRegions', '').split(',')
    cross_region_replication = os.getenv('CrossRegionReplication', 'false').lower() == 'true'
    cross_region_destination_regions = os.getenv('CrossRegionDestinationRegions', '').split(',')

    # Construct the destinations for cross-account replication
    cross_account_destinations = []
    if cross_account_replication:
        for account_id in cross_account_destination_account_ids:
            for region in cross_account_destination_regions:
                cross_account_destinations.append({
                    'region': region,
                    'registryId': account_id
                })

    # Construct the destinations for cross-region replication
    cross_region_destinations = []
    if cross_region_replication:
        for region in cross_region_destination_regions:
            cross_region_destinations.append({
                'region': region,
                'registryId': boto_helper.get_registry_id(sts_client)
            })

    # Construct the replication configuration
    replication_configuration = {
        'rules': [
            {
                'destinations': cross_account_destinations + cross_region_destinations
            }
        ]
    }

    try:
        print('event received-', event)
        response = {}
        response['Status'] = 'SUCCESS'
        response['Reason'] = 'Check the cloudwatch logs for stream :  {}'.format(context.log_stream_name)
        response['PhysicalResourceId'] = context.log_stream_name
        response['StackId'] = event['StackId']
        response['RequestId'] = event['RequestId']
        response['LogicalResourceId'] = event['LogicalResourceId']
        response['NoEcho'] = False
        
        if (event['RequestType'] in ['Create']) and ('ServiceToken' in event):
            try:
                # Enable replication with the constructed configuration
                enable_replication(replication_configuration)

                # Return the appropriate message based on the replication settings
                if not cross_account_replication and not cross_region_replication:
                    statusCode = 202
                    message = 'ECR cross-account and cross-region replication is disabled.'
                elif not cross_region_replication:
                    statusCode = 203
                    message = 'ECR cross-region replication is disabled, but cross-account replication is enabled.'
                elif not cross_account_replication:
                    statusCode = 204
                    message = 'ECR cross-account replication is disabled, but cross-region replication is enabled.'
                else:
                    statusCode = 200
                    message = 'ECR cross-region and cross-account replication enabled successfully.'

                print('statusCode : {}, body : {}'.format(statusCode, message))
                
                boto_helper.send_response(event, response, status='SUCCESS', reason='Lambda Completed')
            
            except Exception as e:
                print('Error', e)
                response['Error'] = str(e)
                boto_helper.send_response(event, response, status='FAILED', reason=str(e))
    
        if (event['RequestType'] in ['Delete','Update']) and ('ServiceToken' in event):
            boto_helper.send_response(event, response, status='SUCCESS', reason='Delete/Update event received')
        
        if response['Status'] == 'SUCCESS':
            return {
                'statusCode': 200,
                'message': "Success: Custom resource invocation completed successfully"
            }
        else:
            return {
                'statusCode': 201,
                'message': "Not Invoked: Custom resource invocation is failed"
            }
    
    except Exception as e:
        print("Lambda Execution Error", str(e))
        raise
    
def enable_replication(replication_configuration):
    response = boto_helper.adding_replication_rule(ecr_client, replication_configuration)
    return response
