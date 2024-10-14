"""
It is creating cost monitor in cost explorer service to monitor the cost for all services
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

client = boto3.client('ce',config=config)
ssm_client = boto3.client('ssm',config=config)
ses_client = boto3.client('ses',config=config)

AWS_Region = os.environ['AWS_REGION']
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
        SUBJECT = "ERROR - AWS " + account_id + " Cost Anomaly Monitor "
        message = MIMEMultipart("mixed")
        message['Subject'] = SUBJECT 
        message['From'] = SENDER
        message['To'] = ','.join(recipient_mails)

        html = """ <html>
            <head><style>table, th, td { border: 1px solid black;}</style></head>
            <body>
            <p style = "font-weight: bold;font-size: 20px;color:red;">Cost Anomaly Is Failed To Create</style></p>
            <p>Hi Team,</p>
            <p>Cost Anomaly is failed to create because of CWCostAnomalyDetection feature is deployed in some other region 
            and it is account level feature, it will not work in multiple region.</p>
            <p>Kindly find the other region where this feature is already deployed</p>
             """
    
        html = html + """
            <p> Thanks! </p>
            <p> Regards, </p>
            <p> CloudOps Automation </p>
            
        </body>
        </html>
        """
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
            response_cost = client.create_anomaly_monitor(
                AnomalyMonitor={
                    'MonitorName': 'cost-anomaly-detection',
                    'MonitorType': 'DIMENSIONAL',
                    'MonitorDimension': 'SERVICE'
                }  
            )
        elif event['RequestType'] == 'Delete':
            response_anomaly = client.get_anomaly_monitors()
            for anomaly in response_anomaly['AnomalyMonitors']:
                if anomaly['MonitorName'] == 'cost-anomaly-detection':
                    monitor_arn = anomaly['MonitorArn']
                    client.delete_anomaly_monitor(
                        MonitorArn=monitor_arn
                    )
        else:
            print("Cost anomlay monitor is alredy created in Cost exploreer service into Dynamodb table in previous version")
        send_response(event, response, status='SUCCESS', reason='Lambda Completed')  
    except Exception as e:
        account_id = boto3.client("sts").get_caller_identity()["Account"]
        create_html_body(account_id)
        print("Error in lambda_handler ",e)
        response['Error'] = str(e)
        send_response(event, response, status='SUCCESS', reason=str(e))