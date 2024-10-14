"""
This Lambda function is used to collect data from the event and send an email to all the verified recipients.

This Lambda is a part of Selfheal crowdstrike agent failure.
 In dxcms_sh_cs_sfn_resolution state machine(SendEmail)
 gets executed after DynamoDbLogging.

Input event of the lambda function is:
{
	"selfHealJobId":"<selfHealJobId>",
}
using selfhealjobid this script takes input from selfheal dynamodb table. 

In resolution state machine,
On successful check, next state SnowDescriptionInput is called.
On FAILURE, next step SendEmailError and then NotifyForLambaFunctionFailure.

"""

import os
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from botocore.config import Config
import json
import traceback

config=Config(retries=dict(max_attempts=10,mode='standard'))

ses_client = boto3.client('ses',config=config)
db_client = boto3.client('dynamodb',config=config)
SenderEmailId = os.environ['SenderEmailId']
CloudOpsEmailIdsParameter = os.environ['CloudOpsEmailIds']
MsTeamsChannelEmailId = os.environ['MsTeamsChannelEmailId']
region = os.environ['AWS_REGION']
table_name = os.environ['table_name']

def success_token(event,task_token):
    try:
        print("success_token() triggered.")
        sf = boto3.client('stepfunctions',config=config)
        sf_output = json.dumps(event)
        sf_response = sf.send_task_success(
            taskToken=task_token,
            output=str(sf_output)
        )
        print("success task token sent - ", sf_response)
        return sf_response
    except Exception as e:
        print("Error success_token() - ",e)
        print("not able to send task success token.")
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

def failure_token(taskToken, error, err_cause):
    try:
        print("failure_token() triggered.")
        if isinstance(err_cause, dict):
            cause = json.dumps(err_cause)
        else:
            cause = str(err_cause)
        sf = boto3.client('stepfunctions',config=config)
        sf_response = sf.send_task_failure(
            taskToken=taskToken,
            error = json.dumps(error),
            cause = cause
        )
        print('failure task token sent - ',sf_response)
    except Exception as e:
        print("Error failure_token() - ", e)
        print("not able to send failure task token")
        raise

# takes email input by calling read_ssm_parameter()
# if an email is present in verified identities and it's status is verified, it accepts that email as recipient.
# else for any other case it will reject that email
# returns recipient_mails
def read_verified_email():
    try:
        print("read_verified_email triggered.")
        emails = read_ssm_parameter().split(',')
        rejected_mails = []
        response = ses_client.get_identity_verification_attributes(
            Identities=emails
        )
        for i in emails:
            if i in response['VerificationAttributes'].keys():
                if response['VerificationAttributes'][i]['VerificationStatus'] == 'Success':
                    continue
            
            rejected_mails.append(i)
            
        print("emails not verified: " + str(rejected_mails))

        recipient_mails = list(set(emails) - set(rejected_mails))
        print("verified emails: " + str(recipient_mails))
        
        return recipient_mails
    except Exception as e:
        print("Error read_verified_email() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

# reads email ids present in ssm parameter
# return all emails mentioned in ssm parameter

def check_sender_status(sender):
    try:
        print("check_sender_status() triggered.")
        status = False
        response = ses_client.get_identity_verification_attributes(
            Identities=[sender, ]
        )
        if sender in response['VerificationAttributes']:
            if response['VerificationAttributes'][sender]['VerificationStatus'] == 'Success':
                status = True
        
        print(f"Sender Verified: {status}")
        return status
    except Exception as e:
        print("Error check_sender_status() - ",e)
        return False

def read_ssm_parameter():
    try:
        print("read_ssm_parameter triggered.")
        ssm = boto3.client('ssm',config=config)
        response_ops_email = ssm.get_parameter(
            Name = CloudOpsEmailIdsParameter
        )
        email_1 = response_ops_email['Parameter']['Value']
        
        response_msteams = ssm.get_parameter(
            Name = MsTeamsChannelEmailId
        )
        email_2 = response_msteams['Parameter']['Value']

        emails = email_1 + ',' + email_2

        print("all input emails: " + str(emails))
        return emails
    except Exception as e:
        print("Error read_ssm_parameter() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())
    
def read_ddb_table(event):
    try:
        print("read_ddb_table triggered.")
        selfHealJobId = event['selfHealJobId']

        response = db_client.get_item(
            TableName=table_name,
            Key={
                'selfHealJobId': {
                    'S': selfHealJobId,
                }
            }
        )

        return response
    except Exception as e:
        print("Error read_ddb_table() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())


def html_body(event):
    try:
        print("html_body triggered.")
        db_table_res = read_ddb_table(event)
        selfheal_result = json.loads(db_table_res['Item']['SelfHealResolutionResult']['S'])
        falcon_agent_status = selfheal_result["falcon_agent_status"]
    
        table = "<table>"
        table = table + "<tr><td>falcon_agent_status </td><td>" + selfheal_result["falcon_agent_status"] + "</td></tr>"
        table = table + "<tr><td>selfHealJobId </td><td>" + selfheal_result["selfHealJobId"] + "</td></tr>"
        table = table + "<tr><td>instance_id </td><td>" + selfheal_result["instance_id"] + "</td></tr>"
        table = table + "<tr><td>instance_iam_status </td><td>" + selfheal_result["instance_iam_status"] + "</td></tr>"
        table = table + "<tr><td>instance_iam_role </td><td>" + selfheal_result["instance_iam_role"] + "</td></tr>"
        table = table + "<tr><td>instance_state </td><td>" + selfheal_result["instance_state"] + "</td></tr>"
        table = table + "<tr><td>ssm_ping_status </td><td>" + selfheal_result["ssm_ping_status"] + "</td></tr>"
        table = table + "<tr><td>instance_cli_status </td><td>" + selfheal_result["instance_cli_status"] + "</td></tr>"
        

        if("platform_type" in selfheal_result and "platform_name" in selfheal_result):
            table = table + "<tr><td>platform_type </td><td>" + selfheal_result["platform_type"] + "</td></tr>"
            table = table + "<tr><td>platform_name </td><td>" + selfheal_result["platform_name"] + "</td></tr>"
            table = table + "<tr><td>public_ip_address </td><td>" + selfheal_result["public_ip_address"] + "</td></tr>"
            table = table + "</table>"
        else:
            table = table + "<tr><td>platform_type </td><td>" + "" + "</td></tr>"
            table = table + "<tr><td>platform_name </td><td>" + "" + "</td></tr>"
            table = table + "<tr><td>public_ip_address </td><td>" + "" + "</td></tr>"
            table = table + "</table>"

        if(falcon_agent_status == "installed_running"):
            html = """
            <html>
            <head>
            <style> 
            table, th, td {{ border: 2px solid black; }}
            th, td {{ border: 1.5px solid black; background-color: #f0f0f0; }}
            </style>
            </head>
            <body><p>Hi Team, </p>
            <p>CrowdStrike/Falcon Agent for {instance_id} is now installed<br>
            Please find CrowdStrike/Falcon Agent Failure SelfHeal data.<br>
            For more information, please refer '{table_name}' dynamoDB table with selfHealJobId as Partition Key.</p>
            <p>{table}</p>
            <p>Regards,<br>
            AWS Selfheal Team </p>
            </body></html>
            """
            html = html.format(instance_id = selfheal_result["instance_id"],table_name = table_name,table = table)
        else:
            html = """
            <html>
            <head>
            <style> 
            table, th, td {{ border: 2px solid black; }}
            th, td {{ border: 1.5px solid black; background-color: #f0f0f0; }}
            </style>
            </head>
            <body><p>Hi Team, </p>
            <p>CrowdStrike/Falcon Agent is NOT installed for {instance_id}.<br>
            Please find CrowdStrike/Falcon Agent Failure SelfHeal data.<br>
            For more information, please refer '{table_name}' dynamoDB table with selfHealJobId as Partition Key.</p>
            <p>{table}</p>
            <p>Regards,<br>
            AWS Selfheal Team </p>
            </body></html>
            """
            html = html.format(instance_id = selfheal_result["instance_id"],table_name = table_name,table = table)
        
        return html
    except Exception as e:
        print("Error html_body() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

# input : event data, recipients mail ids & html body
# calls 'send_raw_email' method from ses client of boto3 library.
# sends mail to all the verified recipient mail ids.
# Email will have different subject based on the StateMachine name.
def send_mail(event,recipient_mails,html):
    try:
        print("send_mail triggered.")
        ssm_client = boto3.client('ssm',config=config)
        response = ssm_client.get_parameter(
            Name = SenderEmailId
        )
        sender = response['Parameter']['Value']

        try:
            AccountName = boto3.client('iam',config=config).list_account_aliases()['AccountAliases'][0]
        except:
            print("AccountName not found, confirm if account alias is created and there are sufficient permissions.")

        msg = MIMEMultipart('mixed')
        msg['Subject'] = "AWS " + AccountName + " " + region + " | " + event['instance_id'] + " | " + "CrowdStrike Agent Failure SelfHeal Data"
        msg['From'] = sender
        msg['To'] = ','.join(recipient_mails)

        msg_body = MIMEMultipart("alternative", None, [MIMEText(html,'html')])
        msg.attach(msg_body)

        sender_status = check_sender_status(sender)
        if sender_status:
            response = ses_client.send_raw_email(
                Source=sender,
                Destinations=recipient_mails,
                RawMessage={
                    'Data': msg.as_string()
                },
            )
            print("email sent.")
        else:
            print(f"email NOT sent. Sender email address '{sender}' is NOT verified. Please verify from Amazon SES console.")
    except Exception as e:
        print("Error send_mail() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

# calls read_verified_email() for recipient mails
# calls html_body(event) for html body.
# calls send_mail() and passes verified mails and html body along with event data
def lambda_handler(event, context):
    global task_token, instance_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    if ("instance_id" in event):
        instance_id = event["instance_id"]
    else:
        instance_id = event[0]["instance_id"]
    try:
        event1 = event[0]
        recipient_mails = read_verified_email()
        html = html_body(event1)
        if recipient_mails:
            send_mail(event1,recipient_mails,html)
        else:
            print("No valid/verified recipients. Email not sent.")

        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        return failure_token(task_token, input, traceback.format_exc())
