'''
boto_helper class constains all the methods related to boto3 operations
'''
import boto3
import json
import time
import urllib.parse
import http.client
from botocore.config import Config


class BotoHelper():
    def __init__(self):
        self.config = Config(retries=dict(max_attempts=10, mode='standard'))
        self.tags = [{'Key': 'Owner', 'Value': 'DXC'}, {'Key': 'Application', 'Value': 'AWS Managed Services'}]
        self.wafv2_client = boto3.client('wafv2', config=self.config)
        self.sts_client = boto3.client('sts', config=self.config)

    def existing_associated_resource_on_Webacl(self, wafv2_client, web_acl_id):
        try:
            existing_associated_resources_response = self.wafv2_client.list_resources_for_web_acl(WebACLArn=web_acl_id, ResourceType='APPLICATION_LOAD_BALANCER')
            print("Existing_Resource_Associated_with_Webacl_Response =====> ", existing_associated_resources_response)
            return existing_associated_resources_response['ResourceArns']
        except Exception as e:
            print("Error occurred while retrieving associated resources from the webacl", str(e))
            raise

    def associating_lb_to_webacl(self, wafv2_client, web_acl_id, lb_arns):
        retry_attempts = 5  # Number of retry attempts
        retry_delay = 120   # Initial retry delay in seconds
        for attempt in range(retry_attempts):
            try:
                for lb_arn in lb_arns:
                    alb_association_to_webacl_response = self.wafv2_client.associate_web_acl(WebACLArn=web_acl_id, ResourceArn=lb_arn)
                    print("ALBAssociationToWebAclResponse ===> ", alb_association_to_webacl_response)
                return alb_association_to_webacl_response
            except wafv2_client.exceptions.WAFUnavailableEntityException as e:
                print("Error (related to WAFUnavailableEntityException): ", str(e))
                if attempt < retry_attempts-1:
                    print("Retrying after {} seconds.".format(retry_delay))
                    time.sleep(retry_delay)
                    retry_delay *= 2  # double retry delay for next attempt
            except Exception as e:
                print("An error occurred hence, unable to associate Load balancer to webAcl : ", str(e))
                raise

    def disassociating_lb_from_webacl(self, wafv2_client, lb_arns):
        try:
            for lb_arn in lb_arns:
                alb_disassociation_from_webacl_response = self.wafv2_client.disassociate_web_acl(ResourceArn=lb_arn)
                print("ALBDisassociationFromWebAclResponse ===> ", alb_disassociation_from_webacl_response)
            return alb_disassociation_from_webacl_response
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Load Balancer(s) are successfully disassociated from the WebACL and Now CloudFormation stack will be deleted with DELETE_COMPLETE status")
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
