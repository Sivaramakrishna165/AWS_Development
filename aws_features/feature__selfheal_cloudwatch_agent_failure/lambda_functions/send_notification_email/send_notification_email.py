"""
This Lambda function is used to collect data from the event and send an email to all the verified recipients.

This Lambda is a part of Selfheal cloudwatch agent failure.
In dxcms_sh_cw_sfn_resolution state machine(SendEmail)
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
    error_status = False
    try:
        print("read_verified_email triggered.")
        emails, error_status = read_ssm_parameter()
        if not error_status:
            emails = emails.split(',')
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
        else:
            print(f"Error while reading {CloudOpsEmailIdsParameter}/{MsTeamsChannelEmailId} ssm parameter: {error_status}.")
            return recipient_mails, f"Error while reading {CloudOpsEmailIdsParameter}/{MsTeamsChannelEmailId} ssm parameter: {error_status}."
        
        return recipient_mails, error_status
    except Exception as e:
        print("Error read_verified_email() - ",e)
        error_status = traceback.format_exc()
        return [], error_status

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
    error_status = False
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
        return emails, error_status
    except Exception as e:
        print("Error read_ssm_parameter() - ",e)
        error_status = traceback.format_exc()
        return [], error_status

    
def read_ddb_table(event):
    error_status = False
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
        return response, error_status
    except Exception as e:
        print("Error read_ddb_table() - ",e)
        error_status = traceback.format_exc()
        return {}, error_status


def html_body(event):
    error_status = False
    try:
        print("html_body triggered.")
        db_table_res, error_status = read_ddb_table(event)
        if not error_status:
            selfheal_result = json.loads(db_table_res['Item']['SelfHealResolutionResult']['S'])
            latest_cloudwatch_logs = selfheal_result["latest_cloudwatch_logs"]
        
            #data = [["selfHealJobId ",event["selfHealJobId"]],["instance_id ",event["instance_id"]],["Instance_Tags_Status ",event["Instance_Tags_Status"]],["Missing_Tags ",event["Missing_Tags"]],["Instance_IAM_Status ",event["Instance_IAM_Status"]],["Instance_IAM_Role ",event["Instance_IAM_Role"]],["Required_Policies ",event["Required_Policies"]],["Instance_State ",event["Instance_State"]],["Instance_SSM_Status ",event["Instance_SSM_Status"]],["SSM_Agent_Version ",event["SSM_Agent_Version"]],["SSM_Ping_Status ",event["SSM_Ping_Status"]],["Instance_CLI_Status ",event["Instance_CLI_Status"]],["State MAchine Execution_Id ",event["Execution"]],["StateMachine ",event["StateMachine"]]]

            table = "<table>"
            table = table + "<tr><td>selfHealJobId </td><td>" + selfheal_result["selfHealJobId"] + "</td></tr>"
            table = table + "<tr><td>instance_id </td><td>" + selfheal_result["instance_id"] + "</td></tr>"
            table = table + "<tr><td>instance_iam_status </td><td>" + selfheal_result["instance_iam_status"] + "</td></tr>"
            table = table + "<tr><td>instance_iam_role </td><td>" + selfheal_result["instance_iam_role"] + "</td></tr>"
            table = table + "<tr><td>instance_state </td><td>" + selfheal_result["instance_state"] + "</td></tr>"
            table = table + "<tr><td>ssm_ping_status </td><td>" + selfheal_result["ssm_ping_status"] + "</td></tr>"
            table = table + "<tr><td>cw_agent_status </td><td>" + selfheal_result["cw_agent_status"] + "</td></tr>"
            table = table + "<tr><td>configfile_status </td><td>" + selfheal_result["configfile_status"] + "</td></tr>"
            table = table + "<tr><td>latest_cloudwatch_logs </td><td>" + selfheal_result["latest_cloudwatch_logs"] + "</td></tr>"
            table = table + "<tr><td>latest_log_after_fix </td><td>" + selfheal_result["latest_log_after_fix"] + "</td></tr>"

            if("platform_type" in selfheal_result and "platform_name" in selfheal_result):
                table = table + "<tr><td>platform_type </td><td>" + selfheal_result["platform_type"] + "</td></tr>"
                table = table + "<tr><td>platform_name </td><td>" + selfheal_result["platform_name"] + "</td></tr>"
                table = table + "</table>"
            else:
                table = table + "<tr><td>platform_type </td><td>" + "" + "</td></tr>"
                table = table + "<tr><td>platform_name </td><td>" + "" + "</td></tr>"
                table = table + "</table>"

            if(latest_cloudwatch_logs == "present"):
                html = """
                <html>
                <head>
                <style> 
                table, th, td {{ border: 2px solid black; }}
                th, td {{ border: 1.5px solid black; background-color: #f0f0f0; }}
                </style>
                </head>
                <body><p>Hi Team, </p>
                <p>CloudWatch Logs for {instance_id} are now successfully generating.<br>
                Please find CloudWatch Agent Failure SelfHeal data.<br>
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
                <p>CloudWatch Logs for {instance_id} are not getting generated.<br>
                Please find CloudWatch Agent Failure SelfHeal data.<br>
                For more information, please refer '{table_name}' dynamoDB table with selfHealJobId as Partition Key.</p>
                <p>{table}</p>
                <p>Regards,<br>
                AWS Selfheal Team </p>
                </body></html>
                """
                html = html.format(instance_id = selfheal_result["instance_id"],table_name = table_name,table = table)
        else:
            print(f"Error while reading dynamodb table {table_name} with partition key {event['selfHealJobId']}: {error_status}")
            return "", error_status
        return html, error_status
    except Exception as e:
        print("Error html_body() - ",e)
        error_status = traceback.format_exc()
        return "", error_status

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
        except Exception as e:
            print("Error while reading AccountName. Proper AccountAliases for this customer account should be provided.")
            input = {"error" : f"Provided proper AccountAliases {str(e)}", "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
            failure_token(task_token, input, traceback.format_exc())

        msg = MIMEMultipart('mixed')
        msg['Subject'] = "AWS " + AccountName + " " + region + " | " + event['instance_id'] + " | " + "CloudWatch Agent Failure SelfHeal Data"
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
        print(f"Email NOT sent, caught error: {traceback.format_exc()}")

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
    error_status = False
    try:
        event1 = event[0]
        recipient_mails, error_status = read_verified_email()
        if not error_status:
            html, error_status = html_body(event1)
            if not error_status:
                send_mail(event1,recipient_mails,html)
            else:
                print(f"Check for key 'SelfHealResolutionResult' in dynamodb {table_name} for partition key {event['selfHealJobId']}.")
        else:
            print("Error while reading verified recipient emails. Email not sent.")
            print(f"Check {CloudOpsEmailIdsParameter} and {MsTeamsChannelEmailId} ssm parameters. Should contain proper verified emails.")

        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())