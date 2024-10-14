import json
import os
import boto3
from boto_helper import BotoHelper

# Create an instance of BotoHelper
boto_helper = BotoHelper()

def lambda_handler(event, context):
    try:
        print('event received-', event)
        response = {}
        response['Status'] = 'SUCCESS'
        response['Reason'] = 'Check the cloudwatch logs for stream :  {}'.format(context.log_stream_name)
        response['PhysicalResourceId'] = 'CustomResourcePhysicalID'
        response['StackId'] = event['StackId']
        response['RequestId'] = event['RequestId']
        response['LogicalResourceId'] = event['LogicalResourceId']
        response['NoEcho'] = False
        
        # Retrieving value of SSMDocumentName and FigServerName from Environment Variable
        ssm_document_name = os.environ['SSMAutomationDocumentName']
        fig_server_name = os.environ['FigServerName']

        if (event['RequestType'] in ['Create', 'Update']) and ('ServiceToken' in event):
            try:
                # Executing the SSM Document
                start_ssm_automation = boto_helper.execute_ssm_document(ssm_document_name, fig_server_name)
                print("START_SSM_AUTOMATION_RESPONSE ====>", start_ssm_automation)
                # Sending the success response
                boto_helper.send_response(event, response, status='SUCCESS', reason='Lambda Completed')
            
                success_response = {
                    'Status': 'SUCCESS',
                    'Data': {
                        'message': 'SSM Document executed successfully!'
                    }
                }
                print("Success_Response - ", success_response)

            except Exception as e:
                print('Error', e)
                response['Error'] = str(e)
                boto_helper.send_response(event, response, status='FAILED', reason=str(e))
                
                failed_response = {
                    'Status': 'FAILED',
                    'PhysicalResourceId': context.log_stream_name,
                    'Data': {
                        'Message': 'Error executing the SSM Document: ' + str(e)
                    }
                }
                print("Failed_Response - ", failed_response)

        if (event['RequestType'] in ['Delete']) and ('ServiceToken' in event):
            boto_helper.send_response(event, response, status='SUCCESS', reason='Delete event received')
        
        return {
            'statusCode': 200,
            'message': "Custom Resource is executed successfully!!"
        }            
    except Exception as e:
        print('Lambda Execution Error ',e)                   