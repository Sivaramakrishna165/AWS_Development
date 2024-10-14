"""
Checks the verification status of recipient email ids mentioned in 
“/DXC/SelfHeal/CloudOpsNotifyEmail” and “/DXC/SelfHeal/MsTeamsChannelEmailId” SSM parameter. 
Creates a formatted html string from the diagnosis result with email content.
Checks verification status of sender email id mentioned in “/DXC/SelfHeal/SenderEmailId” parameter. 
If sender email id if verified, sends an email to verified recipients with the formatted email content. 

This Lambda is a part of Selfheal EC2 NativeBackupFailure

In ExecuteBackup state machine (dxcms_sh_nbf_sfn_execute_backup):
gets executed after - DynamodbLogging
On successful check, next state - SnowDescriptionInput
On FAILURE, next State - TriggerNotificationSfnWError and NotifyForLambaFunctionFailure.
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
SenderEmailIdParameter = os.environ['SenderEmailIdParameter']
CloudOpsEmailIdsParameter = os.environ['CloudOpsEmailIdsParameter']
MsTeamsChannelEmailIdParameter = os.environ['MsTeamsChannelEmailIdParameter']
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
        failure_token(task_token, str(e)[:200], traceback.format_exc())

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
            print(f"Error while reading {CloudOpsEmailIdsParameter}/{MsTeamsChannelEmailIdParameter} ssm parameter: {error_status}.")
            return [], f"Error while reading {CloudOpsEmailIdsParameter}/{MsTeamsChannelEmailIdParameter} ssm parameter: {error_status}."
        
        return recipient_mails, error_status
    except Exception as e:
        print("Error read_verified_email() - ",e)
        error_status = traceback.format_exc()
        return [], error_status

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
            Name = MsTeamsChannelEmailIdParameter
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

        table_json = {}
        table_keys = ["backup_validation","selfHealJobId","instance_id","instance_os_type","vault_name",
                      "instance_state","Instance_SSM_Status","instance_iam_status","backup_iam_status","Instance_CLI_Status",
                      "Instance_Tags_Status","region","account_id","execution_id","statemachine_name"]
        for key in table_keys:
            if key in event.keys():
                table_json[key] = event[key]

        if "backup_validation" in event.keys():
            if not event["backup_validation"]:
                if "backup_job_output" in event.keys():
                    table_json["recovery_point_arn"] = event["backup_job_output"]["recovery_point_arn"]
                    table_json["backup_job_id"] = event["backup_job_output"]["backup_job_id"]
                    table_json["backup_state"] = event["backup_job_output"]["state"]
                if "recovery_point_output" in event.keys():
                    table_json["recovery_point_status"] = event["recovery_point_output"]["recovery_point_status"]
        table = json2html.convert(json = table_json)

        if event["backup_validation"]:
            html_para = f'<p> Level {event["backup_level_assigned"]} native backup for instance {event["instance_id"]} has been taken.<br>'
        else:
            html_para = f'<p> Level {event["backup_level_assigned"]} native backup for instance {event["instance_id"]} does not exist within the last 1440 mins.<br>'

        html = f"""
        <html>
        <head>
        <style> 
        table, th, td {{ border: 2px solid black; }}
        th, td {{ border: 1.5px solid black; background-color: #f0f0f0; }}
        </style>
        </head>
        <body><p>Hi Team, </p>
        <p>This is AWS SelfHeal alert.<br>
        {html_para}
        For more information, please refer '{table_name}' dynamoDB table with selfHealJobId as Partition Key.</p>
        <p>{table}</p>
        <p>Regards,<br>
        AWS Selfheal Team </p>
        </body></html>
        """

        return html, error_status
    except Exception as e:
        print("Error html_body() - ",e)
        error_status = traceback.format_exc()
        return "", error_status

def send_mail(event,recipient_mails,html):
    try:
        print("send_mail triggered.")
        ssm_client = boto3.client('ssm',config=config)
        response = ssm_client.get_parameter(
            Name = SenderEmailIdParameter
        )
        sender = response['Parameter']['Value']

        try:
            AccountName = boto3.client('iam',config=config).list_account_aliases()['AccountAliases'][0]
        except Exception as e:
            print("Error while reading AccountName. Proper AccountAliases for this customer account should be provided.")
            AccountName = "NotFound"

        msg = MIMEMultipart('mixed')
        msg['Subject'] = f"AWS {AccountName} {region} | SelfHeal | Ec2 Native Backup Result"
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

def lambda_handler(event, context):
    global task_token, instance_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id = event["instance_id"]
    error_status = False
    try:
        recipient_mails, error_status = read_verified_email()
        if not error_status:
            html, error_status = html_body(event)
            if not error_status:
                if recipient_mails:
                    send_mail(event,recipient_mails,html)
                else:
                    print("No valid/verified recipients. Email not sent.")
            else:
                print("Error while forming email html body. Email not sent")
        else:
            print("Error while reading verified recipient emails. Email not sent.")
            print(f"Check {CloudOpsEmailIdsParameter} and {MsTeamsChannelEmailIdParameter} ssm parameters. Should contain proper verified emails.")

        return success_token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)
        if not error_status:
            error_status = traceback.format_exc()
        failure_token(task_token, str(e)[:200], error_status)