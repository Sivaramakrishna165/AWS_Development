'''
Boto Helper class contain all the supported aws api operations
'''
import json
import boto3
import urllib.parse
import http.client
from botocore.config import Config

class BotoHelper():
    def __init__(self):
        self.config = Config(retries=dict(max_attempts=10, mode='standard'))
        self.tags = [{'Key': 'Owner', 'Value': 'DXC'}, {'Key': 'Application', 'Value': 'AWS Managed Services'}]
        self.ssm_client = boto3.client('ssm', config=self.config)

    def execute_ssm_document(self, ssm_document_name, fig_server_name):
        try:
            response = self.ssm_client.start_automation_execution(
                DocumentName=ssm_document_name,
                Parameters={
                    'Ec2InstanceNameTag': [fig_server_name]
                }   
            )
            print("SSM_Document_Execution_Response ===> ", response)
            return {
                'statusCode': 200,
                'body': 'SSM Document executed successfully',
                'SSMDocumentAutomationExecId': response["AutomationExecutionId"]
            }
        except Exception as e:
            return {
                'statusCode': 400,
                'body': 'Error executing SSM Document: ' + str(e)
            }
    
    #To send the response back to cfn template
    def send_response(self,request, response, status=None, reason=None):
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
            except:
                print("Failed to send the response to the provided URL")
        return response        