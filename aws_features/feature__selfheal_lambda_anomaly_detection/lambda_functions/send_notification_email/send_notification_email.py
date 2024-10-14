"""
    Checks the verification status of recipient email ids mentioned in 
    “/DXC/Notification/DXCNotifyEmail” and “/DXC/SelfHeal/MsTeamsChannelEmailId” SSM parameter. 
    Creates a formatted html string from the diagnosis result with email content.
    Checks verification status of sender email id mentioned in “/DXC/SelfHeal/SenderEmailId” parameter. 
    If sender email id if verified, sends an email to verified recipients with the formatted email content. 

    This Lambda is a part of Selfheal Lambda Anomaly Detection.
    In dxcms_sh_lad_sfn_diagnosis state machine(SendEmail),
    gets executed after DynamoDbLogging step.

    Input event of the lambda function is:
        {"Payload":{
                "resource_id": "example_resource_id",  
                "lambda_execution_details": {
                    "lambda_1_name": {
                        "invocation_sum": 1,
                        "duration_max": 1710.3,
                        "duration_min": 1710.3,
                        "duration_avg": 1710.3
                    },
                    "lambda_2_name" ...
                }  
            }}

    In Diagnosis state machine,
    On successful check, next state - SnowDescriptionInput is called.
    On FAILURE, trigger TriggerNotificationSfnWError and NotifyForLambdaFunctionFailure.
"""

import os
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from botocore.config import Config
import json
import traceback
from json2html import *

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
        input = {"error" : str(e), "resource_id" : resource_id, "resource_type" : "LambdaAnomalyCloudWatchAlarm"}
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
        return '', error_status

def html_body(event):
    error_status = False
    try:
        print("html_body triggered.")

        table_json = {"selfHealJobId": event["selfHealJobId"]}
        for key,value in event["sorted_lambda_execution_details"].items():
            table_json[key] = value
        table_json.update(
            {
                "message_id": event["resource_id"], "AWSAccountId": event["account_id"],
                "StateMachineName": event['statemachine_name'], "ExecutionID": event['execution_id'],
                "Region" :region
            }
        )
        table = json2html.convert(json = table_json)

        html = """
        <html>
        <head>
        <style> 
        table, th, td {{ border: 2px solid black; }}
        th, td {{ border: 1.5px solid black; background-color: #f0f0f0; }}
        </style>
        </head>
        <body><p>Hi Team, </p>
        <p>This is AWS SelfHeal alert. Lambda Anomaly is detected.<br>
        Please find SelfHeal Lambda Functions Execution details sorted on {sorting_filter}.<br>
        For more information, please refer '{table_name}' dynamoDB table with selfHealJobId as Partition Key.</p>
        <p>{table}</p>
        <p>Regards,<br>
        AWS Selfheal Team </p>
        </body></html>
        """
        html = html.format(sorting_filter = event["sorting_filter"],table_name = table_name,table = table)

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
            AccountName = "NotFound"

        msg = MIMEMultipart('mixed')
        msg['Subject'] = f"AWS {event['account_id']} {region} | SelfHeal | Lambda Functions Anomaly Detected"
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
    global task_token, resource_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    resource_id = event["resource_id"]
    error_status = False
    try:
        recipient_mails, error_status = read_verified_email()
        if not error_status:
            html, error_status = html_body(event)
            if not error_status:
                send_mail(event,recipient_mails,html)
            else:
                raise Exception(f"Error html_body().")
        else:
            print("Error while reading verified recipient emails. Email not sent.")
            print(f"Check {CloudOpsEmailIdsParameter} and {MsTeamsChannelEmailId} ssm parameters. Should contain proper verified emails.")

        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        input = {"error" : f"Error lambda_handler() - {str(e)}", "resource_id" : resource_id, "resource_type" : "LambdaAnomalyCloudWatchAlarm"}
        failure_token(task_token, input, error_status)