'''
This Lambda sends mail to notify user about patching activity when activity starts
'''

import boto3
import os
import sys
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from botocore.client import Config
from botocore.retries import bucket
import datetime
from dateutil import relativedelta
import csv
import codecs
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

cloudOpsEmailId = os.environ['cloudOpsEmailId']
SenderEmailId = os.environ['SenderEmailId']

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

def download_file_from_S3_bucket(fileFullName_Local,fileFullName_S3):
    s3client = boto3.client('s3',config=config)
    try:
        #fileFullName_Local = "c:\\temp\\report.csv"
        #Key = 'PATCHING/' + S3_directory_name + '/' + errorLogFileName
        Key = fileFullName_S3 
        print("Key : ", Key)
        print("fileFullName_Local : ", fileFullName_Local)
        s3client.download_file(bucket, Key, fileFullName_Local)          
        #s3client.download_file(bucket_name, "PATCHING/MAY_2021/ServersList/PatchServerList_MAY_23_2021_14_0_4HRS.csv", "c:\\temp\\PatchServerList_MAY_23_2021_14_0_4HRS.csv")
        return True
    except:
        print(PrintException())
        return False

def get_aws_account_info():
    accoundId = ""
    try:
        sts = boto3.client("sts",config=config)
        accoundId = sts.get_caller_identity()["Account"]    
    except:
        print(PrintException())
        accoundId = ""
    return accoundId

def fetch_account_name():
    try:
        account_name = boto3.client('iam').list_account_aliases()['AccountAliases'][0]
    except: 
        print(PrintException())
        account_name = ""
    return account_name


def extract_tagValue(tagValue):
    patchStartDate= None
    patchEndDate = None
    cloudWatchRuleName = None
    downtimeHours = None
    patchGroup = None
    try:
        tagValue1 = tagValue.split("-")[1]
        patchGroup = tagValue.split("-")[0]

        minutes = tagValue1.split("_")[4]
        hours = tagValue1.split("_")[3]
        date = tagValue1.split("_")[1]
        month = tagValue1.split("_")[0]
        year = tagValue1.split("_")[2]
        downtimeHours = tagValue1.split("_")[5]
        downtimeHoursInt = int(downtimeHours.replace("HRS",""))
        cronjobDate = minutes + " " + hours + " " + date + " " + month + " " + "?" + " " + year
        # cloudWatchRuleName = "PE2EA_Install_Patch_" + tagValue
        cloudWatchRuleName = "Install_Patch_" + tagValue + "_" + region
        
        patchInstallDate_str = str(date) + "-" +  str(month) + "-" + str(year) + "-" + str(hours) + "-" + str(minutes)
        patchStartDate = datetime.datetime.strptime(patchInstallDate_str, '%d-%b-%Y-%H-%M')
        patchEndDate = patchStartDate + datetime.timedelta(hours= +downtimeHoursInt)
    except:
        print(PrintException())
    return patchStartDate,patchEndDate,cloudWatchRuleName,downtimeHours,patchGroup,month

def create_HTML_Body(tagValue,patchJobId,patching_type):
    try:
        accoundId = get_aws_account_info()
        account_name = fetch_account_name()
        patchStartDate,patchEndDate,cloudWatchRuleName,downtimeHours,patchGroup,month = extract_tagValue(tagValue)
        table = "<table>"
        table = table + "<tr><td>Patch Job ID</td><td>" + patchJobId + "</td></tr>"
        table = table + "<tr><td>Account ID </td><td>" + str(accoundId) + "</td></tr>"
        table = table + "<tr><td>Account Name </td><td>" + str(account_name) + "</td></tr>"
        table = table + "<tr><td>Region </td><td>" + region + "</td></tr>"
        table = table + "<tr><td>PatchGroup </td><td>" + patchGroup + "</td></tr>"
        table = table + "<tr><td>Patching Month </td><td>" + patchMonth + "</td></tr>"
        table = table + "<tr><td>Patch Start Date </td><td>" + str(patchStartDate) + "</td></tr>"
        table = table + "<tr><td>Patch End Date </td><td>" + str(patchEndDate) + "</td></tr>"
        table = table + "<tr><td>Total Downtime Hours </td><td>" + str(downtimeHours) + "</td></tr>"
        table = table + "<tr><td>CloudWatch Rule Name </td><td>" + cloudWatchRuleName + "</td></tr>"
        table = table + "</table>"

        BODY_HTML = """	<html>
                <head><style>table, th, td { border: 1px solid black;}</style></head>
                <body>
                <p style = "font-weight: bold;font-size: 20px;">"""+patching_type+""" PATCHING ACTIVITY STARTED</style></p>
                <p>Hi Team,</p>
                <p>     """+patching_type+""" Patching Activity has been started by automation. Kindly look for the mails/notifications for further updates. </p>
                <p>     Kindly find the ServerList reports for the same for verification. Thanks! </p>
                <p>     """
        BODY_HTML = BODY_HTML + table
        BODY_HTML = BODY_HTML + """ </p><br>
                           <p>Regards,</p>
                           <p>CloudOps Automation</p>
                           </body>
                           </html> """
    except:
        print(PrintException())
    return accoundId,BODY_HTML
    
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

def email_body_content(bucket,S3_directory_name,tagvalue,Patching_type):
    try:
        SENDER = read_ssm_parameter(SenderEmailId)
        SENDER = SENDER[0]
        print("Sender's email_is : ", SENDER)
        #Sender = "rekha@dxc.com"
        recipientMailIDs = read_ssm_parameter(cloudOpsEmailId)
        print("Recipient email_id : ",recipientMailIDs)
        if Patching_type == 'Adhoc'        :
            p_type = 'ADHOC'
        else:
            p_type = 'STANDARD'
        accoundId,BODY_HTML = create_HTML_Body(tagvalue,patchJobId,p_type)
        account_name = fetch_account_name()
        CHARSET = "utf-8"
        SUBJECT = "AWS " + account_name + " PE2EA | Started "+Patching_type+" Patch Installation_" + tagvalue
        message = MIMEMultipart("mixed")
        message['Subject'] = SUBJECT 
        message['From'] = SENDER
        message['To'] = ','.join(recipientMailIDs)
        
        # Create the plain-text and HTML version of your message
        BODY_TEXT = """\
        Hi Team,

        Patching Activity has been started by automation. Kindly look for the mails/notifications for further updates. 
        Kindly find the ServerList reports for the same for verification. Thanks!
        Thanks!

        Regards,
        CloudOps Automation"""
        '''BODY_HTML = """\
        <html>
        <body>
            <p>Hi Team,<br>
            How are you?<br>
            </p>
        </body>
        </html>
        """
        '''
        #BODY_HTML = MIMEText(BODY_HTML, "html")
        try:
            fileFullName_Local = local_Folder + "PatchServerList_" + tagvalue + ".csv"
            fileFullName_S3 = S3_Folder_Name + "/" + "PATCHING/" + S3_directory_name + "/ServersList/PatchServerList_" + tagvalue + ".csv"
            attachmentFile = "PatchServerList_" + tagvalue + ".csv"
            download_file_from_S3_bucket(fileFullName_Local,fileFullName_S3)
            #attachmentFile = local_Folder + attachmentFile
            print("attachmentFilePath : ", local_Folder + attachmentFile)
            print("fileFullName_Local : ", fileFullName_Local)
            msg_body = MIMEMultipart('alternative')
            textpart = MIMEText(BODY_TEXT.encode(CHARSET), 'plain', CHARSET)
            htmlpart = MIMEText(BODY_HTML.encode(CHARSET), 'html', CHARSET)
                
            #msg_body.attach(textpart)
            msg_body.attach(htmlpart)
            os.chdir(local_Folder)
            path = os.path.normpath(f"{os.getcwd()}{os.sep}{attachmentFile}")
            print("Normalized Path:", path)
            att = MIMEApplication(open(path, 'rb').read())
            att.add_header('Content-Disposition','attachment',filename=os.path.basename(path))
            message.attach(att)
            
            message.attach(msg_body)
            
            send_mail(SENDER,recipientMailIDs,message)
        except:
            print(PrintException())
    except:
        print(PrintException())

def lambda_handler(event, context):
    try:
        global local_Folder,bucket
        global region
        global patchJobId
        global patchMonth
        global S3_Folder_Name
        bucket = event["S3_Bucket"]
        Patching_Type = event['Patching_Type']
        S3_directory_name = event['S3_directory_name']
        S3_Folder_Name = event['S3_Folder_Name']
        local_Folder = "/tmp/"
        # local_Folder = "C:\\temp\\"
        tagvalue = event['PatchInstallOn']
        tagvalue = tagvalue.replace("_BY","")
        
        patchMonth = S3_directory_name.split("/")[0]
        region = event['region']
        patchJobId = S3_directory_name.split("/")[2]
    
        email_body_content(bucket,S3_directory_name,tagvalue,Patching_Type)
        return event
    except:
        print(PrintException())

if __name__ == "__main__":
    event1 = {
  "PatchInstallOn": "WIN_TEST-NOV_21_2021_13_30_4HRS_BY",
  "S3_Bucket": "dxc",
  "S3_directory_name": "NOV_2021/ap-south-1/patchJobId_90963df6-46b9-11ec-b2db-8c8caa2990d1",
  "Action": "enable",
  "S3_Folder_Name" : "test",
  "region":"ap-south-1"
}   
    lambda_handler(event1, "")
