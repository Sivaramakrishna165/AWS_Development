"""
This lambda is responsible for checking if SSM Agent is present on an instance or not.if it is not prsent it will send the
notification to cloudopsteam.
sample input  : {
                    "S3_Bucket": "dxcms.patchingautomation.567529657087.us-west-1",
                    "S3_directory_name": "JUN_2023/us-west-1",
                    "S3_Folder_Name": "patching_reports",
                    "region": "us-west-1",
                    "TagValues": [
                        "testing-JUL_5_2023_13_5_4HRS",
                        "DEV-JUL_5_2023_13_5_4HRS"
                    ]
                }
"""


import boto3
import os
from botocore.config import Config
from datetime import date, datetime
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from botocore.exceptions import ClientError

config=Config(retries=dict(max_attempts=10,mode='standard'))
client = boto3.client('ec2')
ses_client = boto3.client('ses',config=config)

AWS_Region = os.environ['AWS_REGION']
cloudOpsEmailId = os.environ['cloudOpsEmailId']
SenderEmailId = os.environ['SenderEmailId']

#Input to this function from event: "instance_id" and 'Instance_State'
#This function calls get_status funtion
#It return event with "Instance_SSM_Status", "SSM_Agent_Version", "SSM_Ping_Status" and "Instance_State" keys

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

def create_html_body(instance_id,tagvalue,account_id,patching_type):
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
        SUBJECT = "ALERT - AWS " + account_id + " PE2EA | SSM Agent Not Running  " + tagvalue
        message = MIMEMultipart("mixed")
        message['Subject'] = SUBJECT 
        message['From'] = SENDER
        message['To'] = ','.join(recipient_mails)

        table = "<table>"
        table = table + "<tr><td>Account ID </td><td>" + str(account_id) + "</td></tr>"
        table = table + "<tr><td>Region </td><td>" + str(AWS_Region) + "</td></tr>"
        table = table + "<tr><td>Tag Value </td><td>" + str(tagvalue) + "</td></tr>"
        table = table + "<tr><td>Instance ID </td><td>" + str(instance_id) + "</td></tr>"


        html = """ <html>
            <head><style>table, th, td { border: 1px solid black;}</style></head>
            <body>
            <p style = "font-weight: bold;font-size: 20px;color:red;">SSM Agent Is Not Running</style></p>
            <p>Hi Team,</p>
            <p>SSM Agent is not running for """ + instance_id + """ which will impact the """ + patching_type + """ patching automation workflow.</p>
            <p>Please fix the issue and ensure SSM agent status is Healthy.</p>
            <p>Kindly find the details in below.</p>
             """
        html = html + table + "</table>"
        
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

def get_instance_ids(tag,patchinstalltag,temppatchinstalltag):
    instancelist = []
    error_msg = False
    try:
        name="tag:"+patchinstalltag
        response_patch = client.describe_instances(
            Filters=[
                {
                    'Name': name,
                    'Values': [tag]
                }
            ]
        )
        for r in response_patch['Reservations']:
            for instance in r['Instances']:
                instancelist.append(instance['InstanceId'])
        name="tag:"+temppatchinstalltag
        response_temp = client.describe_instances(
            Filters=[
                {
                    'Name': name,
                    'Values': [tag]
                }
            ]
        )
        for r in response_temp['Reservations']:
            for instance in r['Instances']:
                instancelist.append(instance['InstanceId'])
    except Exception as e:
        error_msg = True
        print("Error in get_instance_ids : ",e)
    return instancelist,error_msg
    
def get_status(instance_id):
    try:
        print("get_status() triggered.")
        ssm_client = boto3.client('ssm',config=config)
        response = ssm_client.describe_instance_information(
            InstanceInformationFilterList=[
                { 'key': 'InstanceIds', 'valueSet': [ instance_id, ] },
            ],
        )
        if not response['InstanceInformationList']:
            Instance_SSM_Status = 'Not_Present'
            SSM_Agent_Version = 'Not_Present'
            Ping_Status = 'ConnectionLost'
        else:
            Instance_SSM_Status = 'Present'
            SSM_Agent_Version = response['InstanceInformationList'][0]['AgentVersion']
            Ping_Status = response['InstanceInformationList'][0]['PingStatus']
    except Exception as e:
        Instance_SSM_Status = 'Not_Present'
        SSM_Agent_Version = 'Not_Present'
        Ping_Status = 'ConnectionLost'
        print("Error get_status() - ",e)
    return Instance_SSM_Status, SSM_Agent_Version, Ping_Status


def lambda_handler(event, context):
    try:
        Tag_Values=[]
        print("input recieved to this script - " + str(event))
        ssm_client = boto3.client('ssm',config=config)
        ec2_client = boto3.client('ec2',config=config)
        if "TagName" in event.keys():
            Tagname = event['TagName']
            if Tagname == 'Downtime Window':
                patchinstalltag = "PatchInstallOn"
                temppatchinstalltag = "PatchInstallTemp"
                patching_type = 'Standard'
            else:
                patchinstalltag = "AdhocPatchInstallOn"
                temppatchinstalltag = "AdhocPatchInstallTemp"
                patching_type = 'Adhoc'
        elif "Patching_Type" in event.keys():
            Patching_Type = event['Patching_Type']
            if Patching_Type == 'Standard':
                patchinstalltag = "PatchInstallOn"
                temppatchinstalltag = "PatchInstallTemp"
                patching_type = 'Standard'
            else:
                patchinstalltag = "AdhocPatchInstallOn"
                temppatchinstalltag = "AdhocPatchInstallTemp"
                patching_type = 'Adhoc'
        
        if "TagValues" in event.keys():
            Tag_Values = event['TagValues']
        elif 'PatchInstallOn' in event.keys():
            Tag_Values.append(event['PatchInstallOn'])
            # if event["Patch_Phase"] == "pre-patch":
            #     Patch_Phase = "pre-patch"
            # elif event["Patch_Phase"] == "post-patch":
            #     Patch_Phase = "post-patch"
        account_id = boto3.client("sts").get_caller_identity()["Account"]
        for tagvalue in Tag_Values:
            instancelist,error_msg = get_instance_ids(tagvalue,patchinstalltag,temppatchinstalltag)
            if not error_msg:
                for instance_id in instancelist:
                    Instance_SSM_Status, SSM_Agent_Version, Ping_Status = get_status(instance_id)
                    print(instance_id," instance status is ",Ping_Status)
                    if Ping_Status=="ConnectionLost":
                        html=create_html_body(instance_id,tagvalue,account_id,patching_type)
                        # send_mail(html,account_id,tagvalue)
        return event
        # return token(event,task_token)
    except Exception as e:
        print("Error lambda_handler() - ",e)

    

event1 = {"instance_id" : "i-0f4adf69c733b6c84"}

if __name__ == "__main__":
    lambda_handler(event1,"")