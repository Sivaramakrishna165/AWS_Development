
'''
[AWSPE-6822]
This is a custom lambda function, which associates and dissoaciate the Load Balancers with WAF WebAcl when creating and deleting the CF stack.

The event that is passed to this lambda typically looks like this:

{
   "RequestType":"",
   "ServiceToken":"",
   "StackId":"",
   "RequestId":"",
   "LogicalResourceId":"",
   "ResourceProperties": {
      "WafWebAclArn": "",
      "LoadBalancerArns": "lbarn1,lbarn2, ...."
    }
}
'''

import boto3
import json
import os
import re
import time
from boto_helper import BotoHelper

# Create an instance of BotoHelper
boto_helper = BotoHelper()

# Create an WAFV2 client
wafv2_client = boto3.client('wafv2')

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
        response['WafWebAclArn'] = event['ResourceProperties']['WafWebAclArn']
        response['AlbArns'] = event['ResourceProperties']['LoadBalancerArns'].split(',')

        # storing value of webacl_arn and alb_arns into separate variables
        waf_webacl_arn = response['WafWebAclArn']
        alb_arns = response['AlbArns']

        if (event['RequestType'] in ['Create']) and ('ServiceToken' in event):
            try:
                # Associating ALB with WebACL
                associate_alb_to_webacl(waf_webacl_arn, alb_arns)
                time.sleep(3)
                boto_helper.send_response(event, response, status='SUCCESS', reason='Lambda Completed')

                success_response = {
                    'Status': 'SUCCESS',
                    'Data': {
                        'result': 'ALBs associated with WebACL successfully',
                        'message': 'ALBs : {} associated with WebACL :  {} successfully'.format(alb_arns, waf_webacl_arn)
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
                        'Message': 'Error associating ALBs with WebACL : ' + str(e)
                    }
                }
                print("Failed_Response - ", failed_response)

        if (event['RequestType'] in ['Delete']) and ('ServiceToken' in event):
            # Disassociating ALB from WebACL
            disassociate_alb_from_webacl(alb_arns)
            time.sleep(3)
            boto_helper.send_response(event, response, status='SUCCESS', reason='Delete event received')

            success_response = {
                'Status': 'SUCCESS',
                'Data': {
                    'result': 'ALBs disassociated with WebACL successfully',
                    'message': 'ALBs : {} disassociated with WebACL :  {} successfully'.format(alb_arns, waf_webacl_arn)
                }
            }
            print("Success_Response - ", success_response)

        if (event['RequestType'] in ['Update']) and ('ServiceToken' in event):
            response = {}
            response['Status'] = 'SUCCESS'
            response['Reason'] = 'Check the cloudwatch logs for stream :  {}'.format(context.log_stream_name)
            response['PhysicalResourceId'] = 'CustomResourcePhysicalID'
            response['StackId'] = event['StackId']
            response['RequestId'] = event['RequestId']
            response['LogicalResourceId'] = event['LogicalResourceId']
            response['NoEcho'] = False
            response['WafWebAclArn'] = event['ResourceProperties']['WafWebAclArn']
            response['AlbArns'] = event['ResourceProperties']['LoadBalancerArns'].split(',')

            resource_lb_arns_already_exists_on_webacl = retrieve_existing_associated_resource_from_webacl(waf_webacl_arn)
            print("Existing_LB_Associated_with_WebACL  ========> ", resource_lb_arns_already_exists_on_webacl)

            print("ALB_ARNS ========> ", alb_arns, "and type is : ", type(alb_arns))

            # Remove spaces within each ARN
            formatted_arns = [alb_arn.replace(' ', '') for alb_arn in alb_arns]
            print("FORMATTED_ARNS ======> ", formatted_arns, "and type is : ", type(formatted_arns))

            combined_list = list(set(resource_lb_arns_already_exists_on_webacl + formatted_arns))
            print("COMBINED_LIST =====> ", combined_list)
            time.sleep(5)
            # Associate load balancer to webacl
            associate_alb_to_webacl(waf_webacl_arn, combined_list)
            print("Associated ALB(s): ", combined_list)

            print("=============== Waiting for 5 seconds to mitiate propagation delay ===============")
            time.sleep(5)
            print("=============== 5 seconds are completed ==============")

            lb_to_disassociate_list = [lb for lb in resource_lb_arns_already_exists_on_webacl if lb not in formatted_arns]
            print("Disassociated Load Balancers from webacl ====> ", lb_to_disassociate_list)
            
            if lb_to_disassociate_list:
                # DisAssociating load balancer(s) from Webacl
                disassociate_alb_from_webacl(lb_to_disassociate_list)

            time.sleep(10)
            print("=============== Association and Dissociation is completed, Please check the latest Associated Resource in WAF console =================")

            boto_helper.send_response(event, response, status='SUCCESS', reason='Update event received')

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


def retrieve_existing_associated_resource_from_webacl(web_acl_id):
    existing_associated_res_response = boto_helper.existing_associated_resource_on_Webacl(wafv2_client, web_acl_id)
    return existing_associated_res_response


def associate_alb_to_webacl(web_acl_id, lb_arns):
    webAclAlbAssociation_response = boto_helper.associating_lb_to_webacl(wafv2_client, web_acl_id, lb_arns)
    return webAclAlbAssociation_response


def disassociate_alb_from_webacl(lb_arns):
    webAclAlbDisassociation_response = boto_helper.disassociating_lb_from_webacl(wafv2_client, lb_arns)
    return webAclAlbDisassociation_response
