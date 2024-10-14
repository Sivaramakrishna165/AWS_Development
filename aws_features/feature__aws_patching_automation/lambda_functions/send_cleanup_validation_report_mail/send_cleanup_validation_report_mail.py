'''This lambda function is use to send cleanup validation reports
sample event {
  "PatchInstallOn": "PKT-MAY_19_2023_13_5_4HRS",
  "S3_Bucket": "dxcms.patchingautomation.567529657087.ap-southeast-2",
  "S3_directory_name": "MAY_2023/ap-southeast-2/patchJobId_e6ff9914-eb25-11ed-a1b0-b57ad2a3a8c8",
  "S3_Folder_Name": "patching_reports",
  "region": "ap-southeast-2"
}
'''
import os,sys
import boto3
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import json,csv
from botocore.client import Config
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

def IsObjectExists(path):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    for object_summary in bucket.objects.filter(Prefix=path):
        return True
    return False

def download_file_from_S3_bucket(fileFullName_Local,fileFullName_S3):
    s3client = boto3.client('s3',config=config)
    try:
        for i in range(len(fileFullName_Local)):
            #fileFullName_Local = "c:\\temp\\report.csv"
            #Key = 'PATCHING/' + S3_directory_name + '/' + errorLogFileName
            Key = fileFullName_S3[i] 
            print("Key : ", Key)
            print("fileFullName_Local : ", local_Folder + fileFullName_Local[i])
            s3client.download_file(bucket_name, Key, local_Folder + fileFullName_Local[i])          
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
    patchGroup = None
    try:
        patchGroup = tagValue.split("-")[0]
        tagValue = tagValue.split("-")[1]
        month = tagValue.split("_")[0]
        year = tagValue.split("_")[2]
        # cloudWatchRuleName = "PE2EA_Install_Patch_" + tagValu
        print("patchGroup : ",patchGroup)
        print("tagValue : ",tagValue)
        print("month : ",month)
        print("year : ",year)

        
    
    except:
        print(PrintException())
    return patchGroup,month

def create_HTML_Body(tagValue,patch_type):
    accoundId = get_aws_account_info()
    account_name = fetch_account_name()

    try:
        patchGroup,month = extract_tagValue(tagValue)
        table = "<table>"
        table = table + "<tr><td>Patch Job ID</td><td>" + patchJobId + "</td></tr>"
        table = table + "<tr><td>Account ID </td><td>" + str(accoundId) + "</td></tr>"
        table = table + "<tr><td>Account Name </td><td>" + str(account_name) + "</td></tr>"
        table = table + "<tr><td>Region </td><td>" + region + "</td></tr>"
        table = table + "<tr><td>PatchGroup </td><td>" + patchGroup + "</td></tr>"
        table = table + "<tr><td>Patching Month </td><td>" + patchMonth + "</td></tr>"
        table = table + "</table>"

        BODY_HTML = """	<html>
                <head><style>table, th, td { border: 1px solid black;}</style></head>
                <body>
                <p style = "font-weight: bold;font-size: 20px;">CLEANUP VALIDATION REPORTS FOR """+patch_type+""" PATCHING</style></p>
                <p>Hi Team,</p>
                <p>     Kindly find the  CLEANUP VALIDATION for the PatchInstallOn tag and Amazon event bridge Rule</p>
                <p>     If Status is PASS in both reports that means it is clean </p>
                <p>     If Status is FAIL in both reports that means it is not clean</p>
                    """
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
                        # write_csv_file(stepName,invalidemailstr,"Unable to send mail to these mail Ids")
                    send_mail(SENDER,recipientMailIDs,msg)
    except:
        print(PrintException())

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
def list_S3_Bucket_object(S3_Bucket,S3_directory_name,tagValue):
    try:
        s3_client = boto3.client("s3",config=config)
        prefixs = [S3_Folder_Name + "/" + "PATCHING/" + S3_directory_name + "/Cleanup Validation/"]
        S3_Objects = []
        for prefix in prefixs: 
            response = s3_client.list_objects_v2(
                    Bucket = S3_Bucket,
                    MaxKeys=123,
                    Prefix = prefix
                )
            S3_bucket_data = response['Contents']
            S3_keys = [ content['Key'] for content in S3_bucket_data]
            for key in S3_keys: 
                S3_Objects.append(key)
        return S3_Objects
    except:
        print(PrintException())

def read_config_to_send_email(bucket,S3_directory_name,tagValue,patch_type):
    try:
        SENDER = read_ssm_parameter(SenderEmailId)
        print("Sender's email_is : ",SENDER)
        CloudOpsTeamEmail_id = read_ssm_parameter(cloudOpsEmailId)
        print("cloudOps_team_emailids_is : ",CloudOpsTeamEmail_id)
        fileNamesAndEmailIds = {}
        print("Read config to send mail")
    
        downtimeContactEmailIDs = CloudOpsTeamEmail_id
        
        recipientMailIDs = []
        for toMailId in downtimeContactEmailIDs.split(";"):
            if toMailId != "":
                recipientMailIDs.append(toMailId)
                
        accoundId,BODY_HTML = create_HTML_Body(tagValue,patch_type)
        account_name = fetch_account_name()
        fileFullName_S3 = list_S3_Bucket_object(bucket,S3_directory_name,tagValue)
        print("fileFullName_S3 : ",fileFullName_S3)
        fileFullName = []
        attachmentFile = []
        for file in fileFullName_S3:
            index = file.rfind("/") + 1
            length = len(file)
            file_name = file[index:length]
            fileFullName.append(file_name)
            local_Folder_filename = local_Folder + file_name
            attachmentFile.append(local_Folder_filename)

        CHARSET = "utf-8"

        SUBJECT = "AWS " + account_name  +" "+ patch_type + " PE2EA | CLEANUP VALIDATION - " + tagValue     
        
        print("\n\n----------------> ",recipientMailIDs)
        print("tagValue : ", tagValue)
        
        print("\nTo Mail ID : ", recipientMailIDs)
        
        msg = MIMEMultipart('mixed')
        msg['Subject'] = SUBJECT 
        msg['From'] = SENDER 
        msg['To'] = ','.join(recipientMailIDs)
        
        try:
            download_file_from_S3_bucket(fileFullName,fileFullName_S3)
    
            msg_body = MIMEMultipart('alternative')
            htmlpart = MIMEText(BODY_HTML.encode(CHARSET), 'html', CHARSET)
            
            msg_body.attach(htmlpart)

            for File in attachmentFile:
                att = MIMEApplication(open(File, 'rb').read())
                att.add_header('Content-Disposition','File',filename=os.path.basename(File))
                msg.attach(att)
            msg.attach(msg_body)
            send_mail(SENDER,recipientMailIDs,msg)
            
        except:
            print(PrintException())
    except:
        print(PrintException())
 

def lambda_handler(event, context):
    global bucket_name
    global S3_directory_name
    global local_Folder
    global S3_folder
    global region
    global patchJobId
    global patchMonth
    global S3_Folder_Name
    region = event['region']
    tagValue = event['PatchInstallOn']
    bucket_name = event['S3_Bucket']
    S3_directory_name = event['S3_directory_name']
    S3_Folder_Name = event['S3_Folder_Name']
    Patching_Type= event['Patching_Type']
    if Patching_Type == 'Adhoc':
        patch_type = 'ADHOC'
    else:
        patch_type = 'STANDARD'
    # local_Folder = "C:\\temp\\"
    local_Folder = "/tmp/"
    patchJobId = S3_directory_name.split("/")[2]
    patchMonth = S3_directory_name.split("/")[0]
    S3_folder = S3_Folder_Name + "/" + 'PATCHING/' + S3_directory_name 
    read_config_to_send_email(bucket_name,S3_directory_name,tagValue,patch_type)
 
# simple test cases
if __name__ == "__main__":
    event1 = {
  "S3_Bucket": "dxc","S3_directory_name": "NOV_2021/ap-south-1/patchJobId_90963df6-46b9-11ec-b2db-8c8caa2990d1","PatchInstallOn": "WIN_TEST-NOV_21_2021_13_30_4HRS","S3_Folder_Name" : "test","region":"ap-south-1"}  
    lambda_handler(event1, "")
