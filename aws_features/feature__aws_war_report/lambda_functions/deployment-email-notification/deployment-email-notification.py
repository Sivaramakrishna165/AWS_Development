"""
Lambda to trigger the notification for notifying the manual pre-requisites
It doesn't require any input to trigger.
"""
import boto3
from botocore.config import Config
import os
import urllib.parse
import json
import http.client
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from botocore.exceptions import ClientError

config=Config(retries=dict(max_attempts=10,mode='standard'))

ses_client = boto3.client('ses',config=config)

AWS_Region = os.environ['AWS_REGION']
# Monitor_ARN = os.environ['MonitorARN']
cloudOpsEmailId = os.environ['cloudOpsEmailId']
SenderEmailId = os.environ['SenderEmailId']

def send_response(request, response, status=None, reason=None):
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

def read_ssm_parameter(name):
    ssm_para_client = boto3.client('ssm',config=config)
    response = ssm_para_client.get_parameter(
        Name=name,
    )
    ssm_parameter = response['Parameter']
    ssm_parameter_value = ssm_parameter['Value']
    return ssm_parameter_value

def send_mail(SENDER,recipientMailIDs,msg):
    try:
        # print("send_mail triggered.")
        if len(recipientMailIDs) != 0:
            print("Trying to send mail to : ",recipientMailIDs)
            try:
                response = ses_client.send_raw_email(
                    Source=SENDER,
                    Destinations= 
                        recipientMailIDs
                        ,
                    RawMessage={
                        'Data': msg.as_string(),
                        },
                    )
                print("Successfully mail sent")
            except ClientError as e:
                print("Error in sendmail : ",e)
                errormessage = (e.response['Error']['Message'])
                print(errormessage)
                if "Email address is not verified" in errormessage:
                    spliterrormessage = errormessage.split(": ")
                    invalidemailstr = spliterrormessage[1]
                    if "," in invalidemailstr:
                        invalidemails = invalidemailstr.split(", ")
                        for email in range(len(invalidemails)):
                            if invalidemails[email] in recipientMailIDs:
                                recipientMailIDs.remove(invalidemails[email])                        
                    else:                    
                        recipientMailIDs.remove(invalidemailstr)
                        stepName = "Mail Communication"
                    send_mail(SENDER,recipientMailIDs,msg)
        print("email sent.")
    except Exception as e:
        print("Error send_mail() - ",e)

def create_html_body(account_id):
    try:
        print("html_body triggered.")
        SENDER = read_ssm_parameter(SenderEmailId)
        # sender = 's.sanika@dxc.com'
        print("Sender's email_is : ", SENDER)
        CloudOpsTeamEmail_ids = read_ssm_parameter(cloudOpsEmailId)
        print("CloudOpsTeamEmail_ids : ",CloudOpsTeamEmail_ids)
        AccountName = boto3.client('iam',config=config).list_account_aliases()['AccountAliases'][0]
        # account_id = boto3.client("sts").get_caller_identity()["Account"]
        # recipient_mails = ['s.sanika@dxc.com']
        value = CloudOpsTeamEmail_ids
        recipientMailIDs = []
        rejected_mails = []
        for toMailId in value.split(";"):
            if toMailId != "":
                recipientMailIDs.append(toMailId)
        print("\nTo Mail ID : ", recipientMailIDs)
        response = ses_client.get_identity_verification_attributes(
            Identities=recipientMailIDs
        )
        for i in recipientMailIDs:
            if i in response['VerificationAttributes'].keys():
                if response['VerificationAttributes'][i]['VerificationStatus'] == 'Success':
                    continue
            rejected_mails.append(i)
                    
        print("emails not verified: " + str(rejected_mails))

        recipient_mails = list(set(recipientMailIDs) - set(rejected_mails))
        print("verified emails: " + str(recipient_mails))
        CHARSET = "utf-8"
        SUBJECT = "AWS " + account_id + " WAR Report "
        lambda_arn = f"arn:aws:iam::{account_id}:role/dxcms-aws-war-lambda-exec-role-{AWS_Region}"
        message = MIMEMultipart("mixed")
        message['Subject'] = SUBJECT 
        message['From'] = SENDER
        message['To'] = ','.join(recipient_mails)

        table = "<table>"
        table = table + "<tr><td>Account ID </td><td>" + str(account_id) + "</td></tr>"
        table = table + "<tr><td>Account Name </td><td>" + str(AccountName) + "</td></tr>"
        table = table + "<tr><td>Region </td><td>" + AWS_Region + "</td></tr>"
        # table = table + "<tr><td>Bucket Name </td><td>" + bucket_name + "</td></tr>"
        table = table + "<tr><td>Cloud Automation Email</td><td>" + "arnold.qui.ibero@dxc.com" + "</td></tr>"
        table = table + "<tr><td>Lambda Role ARN </td><td>" + lambda_arn + "</td></tr>"
        table = table + "</table>"

        html = """ <html>
                <head><style>table, th, td { border: 1px solid black;}</style></head>
                <body>
                <p style = "font-weight: bold;font-size: 20px;">AWS Well Architected Review - Reporting Automation Pre-requisites</style></p>
                <p>Hello Team,</p>
                <p>Greetings !</p>
                <p>To enable the AWS WAR Reporting Solution, please complete the below pre-requisites on customer AWS accounts.</p>
                <p> •	Please share Customer AWS account details as mentioned below to Automation Team Email. </p>
                <p>     """
        html = html + table
        html = html + """  <p>•	Request access for Centralized PowerBI Dashboard using this https://app.powerbi.com/reportEmbed?reportId=d01288f4-9a7f-44a7-9f94-b8d50aba450b&appId=33a60d5a-0c3b-4a2e-81de-b1f2759e25fd&autoAuth=true&ctid=93f33571-550f-43cf-b09f-cd331338d086.</p>
                            </p><br>
                           <p>Regards,</p>
                           <p>Cloud Automation Team</p>
                           </body>
                           </html> """ 
        try:
            msg_body = MIMEMultipart('alternative')
            # textpart = MIMEText(BODY_TEXT.encode(CHARSET), 'plain', CHARSET)
            htmlpart = MIMEText(html.encode(CHARSET), 'html', CHARSET)                
            # msg_body.attach(textpart)
            msg_body.attach(htmlpart)
            message.attach(msg_body) 
            #print(type(message))
            # send_mail(html,account_id,tagvalue)         
            send_mail(SENDER,recipient_mails,message)
        except Exception as e:
            print("error in in msg body : ",e)
    except Exception as e:
        error_status = True 
        html=''
        print("Error html_body() - ",e)

def lambda_handler(event, context):
    try:
        print('Received event is ',event)
        response = {}
        response['Status'] = 'SUCCESS'
        response['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
        response['PhysicalResourceId'] = context.log_stream_name
        response['StackId'] = event['StackId']
        response['RequestId'] = event['RequestId']
        response['LogicalResourceId'] = event['LogicalResourceId']
        response['NoEcho'] = False
        if event['RequestType'] == 'Create':
            account_id = boto3.client("sts").get_caller_identity()["Account"]
            create_html_body(account_id)
        send_response(event, response, status='SUCCESS', reason='Lambda Completed')  
    except Exception as e:
        print("Error in lambda_handler ",e)
        response['Error'] = str(e)
        send_response(event, response, status='SUCCESS', reason=str(e))