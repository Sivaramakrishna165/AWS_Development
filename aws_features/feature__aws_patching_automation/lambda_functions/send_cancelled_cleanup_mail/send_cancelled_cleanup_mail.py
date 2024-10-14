'''This lambda function is use to send cleanup validation reports
sample event {
  "S3_Bucket": "dxcms.patchingautomation.567529657087.eu-west-3",
  "S3_directory_name": "AUG_2023/eu-west-3",
  "S3_Folder_Name": "patching_reports",
  "region": "eu-west-3",
  "Tag_Value": "DEV-AUG_10_2023_6_0_3HRS",
  "attribute_value": "cancelled",
  "statusCode": 200,
  "body": "All temporary files deleted.",
  "patchJob_id": "patchJobId_ddf88c56-40a7-11ee-944b-0550d80d8a39",
  "attribute_name": "patch_job_status"
}
'''
import os
import sys
import boto3
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import json
from botocore.client import Config
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

cloudOpsEmailId = os.environ['cloudOpsEmailId']
SenderEmailId = os.environ['SenderEmailId']

'''Printexception function is created for handling an error
this function returns the line number where error that occured '''
def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

'''Function to read SSM parameter value'''
def read_ssm_parameter(name):
    try:
        ssm_para_client = boto3.client('ssm',config=config)
        response = ssm_para_client.get_parameter(
            Name=name,
        )
        ssm_parameter = response['Parameter']
        ssm_parameter_value = ssm_parameter['Value']
 
        return ssm_parameter_value
    except:
        print(PrintException())
        
'''Getting account number and account name'''
def get_aws_account_info():
    accoundId = ""
    try:
        sts = boto3.client("sts",config=config)
        accoundId = sts.get_caller_identity()["Account"]
        account_name = boto3.client('iam',config=config).list_account_aliases()['AccountAliases'][0]
    except:
        print(PrintException())
        accoundId = ""
        account_name = ""
    return accoundId, account_name

'''Get CR number from config file'''
def read_data_from_config_file(tagValue):
    try:
        s3client = boto3.client('s3',config=config)
        directory_name = S3_Folder_Name + "/" + "PATCHING" + "/" + S3_directory_name + "/" + "Patching_config.json"
        response = s3client.get_object(Bucket=S3_Bucket, Key=directory_name)
        content = response['Body']
        config_dict = json.loads(content.read())
        #print(type(config_dict), config_dict)
        if 'Change_Request' in config_dict.keys():
            CRnumber = config_dict['Change_Request'][tagValue]
        else:
            CRnumber = 'N/A'
    except:
        print(PrintException())
        CRnumber = 'N/A'
    return CRnumber
    
    
'''Function to send email'''    
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

'''Function to create HTML email body'''
def create_HTML_Body(tagValue,patch_type,report_path,CRnumber):
    try:
        patchGroup = tagValue.split("-")[0]
        table = "<table>"
        table = table + "<tr><td>Patch Job ID</td><td>" + patchJobId + "</td></tr>"
        table = table + "<tr><td>Account ID </td><td>" + str(accoundId) + "</td></tr>"
        table = table + "<tr><td>Account Name </td><td>" + str(account_name) + "</td></tr>"
        table = table + "<tr><td>Region </td><td>" + region + "</td></tr>"
        table = table + "<tr><td>PatchGroup </td><td>" + patchGroup + "</td></tr>"
        table = table + "<tr><td>Patching Month </td><td>" + patchMonth + "</td></tr>"
        table = table + "<tr><td>PatchInstallOn Tag </td><td>" + tagValue + "</td></tr>"
        table = table + "<tr><td>Change Request No. </td><td>" + CRnumber + "</td></tr>"        
        table = table + "</table>"

        BODY_HTML = """	<html>
                <head><style>table, th, td { border: 1px solid black;}</style></head>
                <body>
                <p style = "font-weight: bold;font-size: 20px;">PATCHING WINDOW CANCELLED FOR """+patch_type+""" PATCHING</style></p>
                <p>Hi Team,</p>
                <p>Scheduled Patching Activity has been Cancelled. Details of the cancelled activity are as follows.</p>
                """
        BODY_HTML = BODY_HTML + table
        BODY_HTML = BODY_HTML + """<p>Please update and close the corresponding Change Request raised for this activity.</p>
                           <p>For more details on the cleaned up resources refer S3 bucket path : """+report_path+"""</p><br>
                           <p>Regards,</p>
                           <p>CloudOps Automation</p>
                           </body>
                           </html> """
    except:
        print(PrintException())
    return BODY_HTML, table
    
'''Function to prepare and send final email'''    
def read_config_to_send_email(bucket,S3_directory_name,tagValue,patch_type):
    try:
        SENDER = read_ssm_parameter(SenderEmailId)
        print("Sender's email_is : ", SENDER)

        recipientMailID = read_ssm_parameter(cloudOpsEmailId)
        print("Recipient email_id : ",recipientMailID)
        value = recipientMailID

        recipientMailIDs = []
        for toMailId in value.split(";"):
            if toMailId != "":
                recipientMailIDs.append(toMailId)
        print("\nTo Mail ID : ", recipientMailIDs)
        
        CRnumber = read_data_from_config_file(tagValue)
        CHARSET = "utf-8"
        SUBJECT = "AWS "+ account_name + " PE2EA | PATCHING WINDOW CANCELLED " + tagValue
        message = MIMEMultipart("mixed")
        message['Subject'] = SUBJECT 
        message['From'] = SENDER
        message['To'] = ','.join(recipientMailIDs)
        
        # Create the plain-text and HTML version of your message
        report_path = bucket+'/'+S3_Folder_Name +'/PATCHING/'+ S3_directory_name +'/Patching-Windows-Cancelled/'
        BODY_HTML, table = create_HTML_Body(tagValue,patch_type,report_path,CRnumber)
        table_text = table.replace("<table>","\n").replace("<tr><td>","\n").replace("</td><td>",":").replace("</td></tr>","").replace("</table>","\n")
        
        BODY_TEXT = """\
            Hi Team,

            Scheduled Patching Activity has been Cancelled. Details of the cancelled activity are as follows. 
            
            """+table_text+"""
            Please update and close the corresponding Change Request raised for this activity.
            For more details on the cleaned up resources refer S3 bucket path : """+report_path+"""
            Thanks!

            Regards,
            CloudOps Automation"""

        #BODY_HTML = MIMEText(BODY_HTML, "html")
        try:
            msg_body = MIMEMultipart('alternative')
            textpart = MIMEText(BODY_TEXT.encode(CHARSET), 'plain', CHARSET)
            htmlpart = MIMEText(BODY_HTML.encode(CHARSET), 'html', CHARSET)
                
            msg_body.attach(textpart)
            msg_body.attach(htmlpart)

            message.attach(msg_body)
            print("Sending Patching Window Missed Notification...")
            send_mail(SENDER,recipientMailIDs,message)
        except:
            print(PrintException())
    except:
        print(PrintException())
 

def lambda_handler(event, context):
    global S3_Bucket
    global S3_directory_name
    global local_Folder
    global S3_folder
    global region
    global patchJobId
    global patchMonth
    global S3_Folder_Name
    global accoundId
    global account_name
    
    region = event['region']
    tagValue = event['Tag_Value']
    S3_Bucket = event['S3_Bucket']
    S3_directory_name = event['S3_directory_name']
    S3_Folder_Name = event['S3_Folder_Name']
    patchJobId = event["patchJob_id"]
    accoundId,account_name = get_aws_account_info()
    
    if "adhoc" in S3_Bucket: patch_type = 'ADHOC' 
    else: patch_type = 'STANDARD'

    local_Folder = "/tmp/"
    patchMonth = S3_directory_name.split("/")[0]
   
    read_config_to_send_email(S3_Bucket,S3_directory_name,tagValue,patch_type)

    return event
    
# simple test cases
if __name__ == "__main__":
    event1 = {
  "S3_Bucket": "dxc",
  "S3_directory_name": "NOV_2021/ap-south-1/patchJobId_90963df6-46b9-11ec-b2db-8c8caa2990d1",
  "PatchInstallOn": "WIN_TEST-NOV_21_2021_13_30_4HRS",
  "S3_Folder_Name" : "test",
  "region":"ap-south-1"
  }  
    lambda_handler(event1, "")
