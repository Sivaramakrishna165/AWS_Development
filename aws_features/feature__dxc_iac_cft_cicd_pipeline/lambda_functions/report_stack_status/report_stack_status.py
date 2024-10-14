'''
NOTE: Lambda function name will be dynamically allocated while stack creation

Lambda function is invoked by *rdxcCICDReportRule* event rule.

Function checks the status of the CFTs created/updated by CICD pipeline.
And the same is updated in DynamoDB table - *rCicdStacksReportDdbTable*
Post creation an email is sent with the CFTs creation/updation report.

Created By: Kedarnath Potnuru
Date: 14 Apr 2023

'''
import json
import boto3
import os
from boto_helper import boto_helper
from email_notification import email_notification

cicd_report_tbl = os.environ['CICDReportDbdTable'].split('/')[-1]
cicd_report_event_rule = 'Empty'
pipeline = os.environ['Pipeline']
account = os.environ['Account']
cross_acc_role = os.environ['CrossAccountRole']
deploy_region = os.environ['Region']
receiver_ssmparam = os.environ['ReceiverMailSSMParam']
sender_ssmparam = os.environ['SenderMailSSMParam']

def lambda_handler(event, context):
    print('Event received',event)
    region = context.invoked_function_arn.split(':')[3]
    cicd_report_event_rule = event['resources'][0].split('/')[-1]
    deploy_region = os.environ['Region']
    if(deploy_region == ''): deploy_region = region
    
    helper_obj = boto_helper(pipeline, deploy_region, cross_acc_role)
    
    if(cross_acc_role ==''):
        deploy_acc = account
    else:
        deploy_acc = cross_acc_role.split('::')[-1].split(':')[0]
    
    
    stacks_lst = helper_obj.describe_stacks()
    bln_complete = True
    for stack in stacks_lst:
        if('progress' in stack['Status'].lower()):
            bln_complete = False
        
        dynamo_payload = {}
        dynamo_payload['StackName'] = stack['StackName']
        dynamo_payload['Status'] = stack['Status']
        dynamo_payload['StackDescription'] = stack['StackDescription']
        dynamo_payload['Comments'] = 'Stack execution status - "{}"'.format(stack['Status'])
        
        helper_obj.add_items(cicd_report_tbl, dynamo_payload)
        print(dynamo_payload)
        
    
    if(bln_complete):
        helper_obj.disable_event_rule(cicd_report_event_rule)
        print(f'Event rule "{cicd_report_event_rule}" disabled successfully.')
        
        dynamo_lst = helper_obj.describe_dynamo_items(cicd_report_tbl)
        
        receiver = helper_obj.get_ssm_param_value(receiver_ssmparam)
        sender = helper_obj.get_ssm_param_value(sender_ssmparam)
        email_obj = email_notification(sender, receiver)
        
        if(len(dynamo_lst)>0 and receiver != 'No-Value' or sender != 'No-Value'):
            email_obj.send_email(dynamo_lst, pipeline, account, deploy_acc, region, deploy_region)

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
