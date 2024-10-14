'''
boto_helper class constains all the methods related to boto3 operations
'''
import boto3
import json
import urllib.parse
import http.client
from botocore.config import Config

class BotoHelper():
    def __init__(self):
        self.config = Config(retries=dict(max_attempts=10, mode='standard'))
        self.tags = [{'Key': 'Owner', 'Value': 'DXC'}, {'Key': 'Application', 'Value': 'AWS Managed Services'}]
        self.ecr_client = boto3.client('ecr', config=self.config)
        self.sts_client = boto3.client('sts', config=self.config)

    def get_registry_id(self, sts_client):
        try:
            account_id = self.sts_client.get_caller_identity().get('Account')
            return account_id
        except:
            raise
    
    def adding_replication_rule(self, ecr_client, replication_configuration):
        try:
            replication_response = self.ecr_client.put_replication_configuration(
            replicationConfiguration=replication_configuration)
            print("Replication_Response ===> ", replication_response)
            return replication_response
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error adding replication rule:", str(e))
            raise

        # To send the response back to cfn template
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
            except:
                print("Failed to send the response to the provided URL")
        return response
