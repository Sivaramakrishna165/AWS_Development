'''
This lambda script is used to notify user about issue on while stopping/starting application using SNS
'''

import boto3
import os
import sys
import json
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from botocore.client import Config
from botocore.retries import bucket
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

cloudOpsEmailId = os.environ['cloudOpsEmailId']
SenderEmailId = os.environ['SenderEmailId']
cloudOpsTeamsChannel =  os.environ['cloudOpsTeamsChannel']


def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

def read_ssm_parameter(name):
    ssm_para_client = boto3.client('ssm',config=config)
    response = ssm_para_client.get_parameter(
        Name=name,
    )
    ssm_parameter = response['Parameter']
    parameter_value = ssm_parameter['Value']
    ssm_parameter_value = parameter_value.split(";")
    return ssm_parameter_value

def send_mail(SENDER,recipientMailIDs,msg):
    try:
        client = boto3.client('ses',config=config)
        if len(recipientMailIDs) != 0:
            print("Trying to send mail to : ",recipientMailIDs)
            try:
                response = client.send_raw_email(
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
                print(PrintException())
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
    except:
        print(PrintException())


def email_body_content(status,Region,Account_id,instanceIds,appIssue,command_id):
    try:
        print("Region ==> ",Region)
        Account = Account_id
        print("Account_id == > ",Account)
        print("Status ==>",status)

        SENDER = read_ssm_parameter(SenderEmailId)
        SENDER = SENDER[0]
        print("Sender's email_is : ", SENDER)

        recipientMailIDs = read_ssm_parameter(cloudOpsEmailId)
        try:
            teamsChannelId = read_ssm_parameter(cloudOpsTeamsChannel)
            recipientMailIDs = recipientMailIDs + ";" + teamsChannelId
        except:
            print(PrintException())
        print("Recipient email_id : ",recipientMailIDs)
        CHARSET = "utf-8"
        SUBJECT = "ERROR - AWS " + Account_id + " PE2EA | Application Failed for Instance : " + instanceIds
        message = MIMEMultipart("mixed")
        message['Subject'] = SUBJECT 
        message['From'] = SENDER
        message['To'] = ','.join(recipientMailIDs)

        # Create the plain-text and HTML version of your message
        BODY_TEXT = """\
        Hi Team,

        Patching Automation is FAILED. "Status". Please find the details in below.
        Error occured on Instance $InstanceId  
        
        Account : $Account_id
        Region : $Region
        Thanks!

        Regards,
        CloudOps Automation"""
        
        table = "<table>"
        table = table + "<tr><td>Instance Id</td><td>" + str(instanceIds) + "</td></tr>"
        table = table + "<tr><td>SSM Command ID </td><td>" + str(command_id) + "</td></tr>"
        table = table + "<tr><td>Account ID </td><td>" + str(Account_id) + "</td></tr>"
        table = table + "<tr><td>Region </td><td>" + str(Region) + "</td></tr>"
        table = table + "<tr><td>Status </td><td>" + str(status) + "</td></tr>"

        BODY_HTML = """ <html>
            <head><style>table, th, td { border: 1px solid black;}</style></head>
            <body>
            <p style = "font-weight: bold;font-size: 20px;color:red;"> """ + appIssue + " Instance ID : " + str(instanceIds) + """ </style></p>
            <p>Hi Team,</p>
            <p>Applicaiton is FAILED for the Instance - """ + instanceIds + """ . Kindly look into it.</p>"""
            
        BODY_HTML = BODY_HTML + table + "</table>"
        
        BODY_HTML = BODY_HTML + """
                                <p> Thanks! </p>
                                <p> Regards, </p>
                                <p> CloudOps Automation 
                                </p>
                            </body>
                            </html>
                            """
        #print("HTML_Body =======> ", BODY_HTML)
        try:
            msg_body = MIMEMultipart('alternative')
            textpart = MIMEText(BODY_TEXT.encode(CHARSET), 'plain', CHARSET)
            htmlpart = MIMEText(BODY_HTML.encode(CHARSET), 'html', CHARSET)                
            #msg_body.attach(textpart)
            msg_body.attach(htmlpart)
            message.attach(msg_body) 
            #print(type(message))          
            send_mail(SENDER,recipientMailIDs,message)
        except:
            print(PrintException())
    except:
        print(PrintException())

def get_PatchInstallOn_tagValue(instanceId):
    try:
        PatchInstallOnValue = ""
        client = boto3.client('ec2',config=config)
        ec2res = boto3.resource('ec2')
        instanceInfo = ec2res.Instance(id=instanceId)
        for tag in instanceInfo.tags:
            if tag['Key'] == "PatchInstallOn":
                PatchInstallOnValue = tag['Value']
                
        if "AY" in PatchInstallOnValue:
            appIssueAt = "UNABLE TO START APPLICATION AFTER PATCHING"
        else:
            appIssueAt = "UNABLE TO STOP APPLICATION TO PERFORM PATCHING"
        return appIssueAt
    except:
        print(PrintException())
    return status
    
def lambda_handler(event, context):
    try:
        sns_records = json.dumps(event['Records'][0])
        sns_dict = json.loads(sns_records)
        eventSubscription = sns_dict['EventSubscriptionArn']
        Topic_Arn_content = eventSubscription.split(":")
        Region = Topic_Arn_content[3]
        Account_id = Topic_Arn_content[4]
        
        sns_message = json.loads(event['Records'][0]['Sns']['Message'])       
        command_id = sns_message["commandId"]
        instanceIds = sns_message["instanceId"]
        status = sns_message["status"]  
        appIssue = get_PatchInstallOn_tagValue(instanceIds)
        email_body_content(status,Region,Account_id,instanceIds,appIssue,command_id)

    except:
        print(PrintException())
    
# simple test cases outputS3BucketName":"dxc","outputS3KeyPrefix ","instanceIds"

event1 = {'Records': [{'EventSource': 'aws:sns', 'EventVersion': '1.0', 'EventSubscriptionArn': 'arn:aws:sns:ap-south-1:338395754338:DXC_SNS_PatchNotifyFailure:d3273f36-96aa-4bf5-af9b-61a72702d7bb', 'Sns': {'Type': 'Notification', 'MessageId': 'bdb2e355-aae0-5810-988e-ba621e4de4e3', 'TopicArn': 'arn:aws:sns:ap-south-1:338395754338:DXC_SNS_PatchNotifyFailure', 'Subject': 'EC2 Run Command Notification ap-south-1', 'Message': '{"commandId":"c3d062dc-fb03-4211-b9d9-689cda1ca9e7","documentName":"AWS-RunPatchBaseline","instanceId":"i-0d5758a7ec1373272","requestedDateTime":"2021-06-07T05:45:05.71Z","status":"Cancelled","detailedStatus":"Cancelled","eventTime":"2021-06-07T05:45:17.683Z"}', 'Timestamp': '2021-06-07T05:45:17.750Z', 'SignatureVersion': '1', 'Signature': 'O5PfckaGTL0/g+AF/BAkOUPbVFP99hyKCKMkOVlsB/u7D5nnTazoB5I32CLYptcQyAB6PTCg9TLudgpqgiofNtHoQVnox7/YW5UFBtd3jj1C42iYIwAY/TCeMtQz2o8U/wEOiWu6nJBet8ErAyw4k2RhpBUW2SkIER1+y/h2KGYazwAT3xP1YXMbraxIGqb/gBzLSI9elOaravprssM0tkHq5mVHY2vTupocRPkeu9u/G+qUdcvAKfyGyMtG15hlS2STaLTQZsGQVnMXc1T+UqxOW5IAv10Y3wko3dRSwnxMerpIWeBT58GUKehR/oq0iR3m4dgwJWoRvJWIx59idA==', 'SigningCertUrl': 'https://sns.ap-south-1.amazonaws.com/SimpleNotificationService-010a507c1833636cd94bdb98bd93083a.pem', 'UnsubscribeUrl': 'https://sns.ap-south-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:ap-south-1:338395754338:DXC_SNS_PatchNotifyFailure:d3273f36-96aa-4bf5-af9b-61a72702d7bb', 'MessageAttributes': {}}}]}


if __name__ == "__main__":
      lambda_handler(event1, "")



