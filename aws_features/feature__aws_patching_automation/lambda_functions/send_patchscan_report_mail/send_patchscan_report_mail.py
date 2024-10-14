'''
This Lambda script sends patch scan report to the user
'''

import os
import sys
import boto3
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import json,csv
from botocore.client import Config
import datetime
from dateutil import relativedelta
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


def create_HTML_Body(Patching_Type,tagValue):
    try:
        accoundId = get_aws_account_info()
        account_name = fetch_account_name()
        patchStartDate,patchEndDate,cloudWatchRuleName,downtimeHours,patchGroup,month = extract_tagValue(tagValue)
        print("Patch Start Date : ", patchStartDate)
        print("Patch End Date : ", patchEndDate)
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
                <p>Hi Team,</p>
                <p style = "font-weight: bold;font-size: 20px;"> """+Patching_Type+""" PRE PATCH COMPLIANCE SCAN REPORT</style></p>
                <p>     Kindly find the PRE PATCH COMPLIANCE SCAN REPORT for the servers which are scheduled for Patching..</p>
                <p>     Find the patch schedule details in below.</p>
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
    
def IsObjectExists(path):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    for object_summary in bucket.objects.filter(Prefix=path):
        return True
    return False
    
def upload_file_into_s3(fileFullName_Local,fileFullName_S3):
    try:
        s3_resource = boto3.resource('s3', config=Config(signature_version='s3v4'))
        bucket = s3_resource.Bucket(bucket_name)
        Key = fileFullName_S3
        print("Key : ", Key)
        print("fileFullName_Local : ",fileFullName_Local)
        bucket.upload_file(fileFullName_Local, Key)
    except:
        print(PrintException())
    
def download_file_from_S3_bucket(fileFullName_Local,fileFullName_S3):
    s3client = boto3.client('s3',config=config)
    try:
        #fileFullName_Local = "c:\\temp\\report.csv"
        #Key = 'PATCHING/' + S3_directory_name + '/' + errorLogFileName
        Key = fileFullName_S3 
        print("Key : ", Key)
        print("fileFullName_Local : ", fileFullName_Local)
        s3client.download_file(bucket_name, Key, fileFullName_Local)          
        #s3client.download_file(bucket_name, "PATCHING/MAY_2021/ServersList/PatchServerList_MAY_23_2021_14_0_4HRS.csv", "c:\\temp\\PatchServerList_MAY_23_2021_14_0_4HRS.csv")
        return True
    except:
        print(PrintException())
        return False

def write_csv_file(stepName,resource,errorMsg):
    try:
        with open(errorLog_Local_FullFileName, 'a', newline='') as csvfile:
            filewriter = csv.writer(csvfile, delimiter=',')        
            filewriter.writerow([stepName,resource,errorMsg])
    except:
        print(PrintException())
    
def read_jsonfile(S3_Bucket,S3_directory_name,Keyname):
    try:
        s3client = boto3.client('s3',config=config)
        jsonConfig_S3_directory_name = S3_directory_name.split("/")
        jsonConfig_S3_directory_name = jsonConfig_S3_directory_name[0] + "/" + jsonConfig_S3_directory_name[1]
        directory_name = S3_Folder_Name + "/" + "PATCHING"+"/"+ jsonConfig_S3_directory_name + "/" + "Patching_config.json"
        print("Patching JSON Config file : ", directory_name)
        response = s3client.get_object(Bucket=S3_Bucket, Key=directory_name)
        content = response['Body']
        jsonObject = json.loads(content.read())
        JsonKey = jsonObject[Keyname]
        return JsonKey
    except:
        print(PrintException())


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
                        write_csv_file(stepName,invalidemailstr,"Unable to send mail to these mail Ids")
                    send_mail(SENDER,recipientMailIDs,msg)
    except:
        print(PrintException())


def read_ssm_parameter(name):
    ssm_para_client = boto3.client('ssm',config=config)
    response = ssm_para_client.get_parameter(
        Name=name,
    )
    ssm_parameter = response['Parameter']
    ssm_parameter_value = ssm_parameter['Value']
    return ssm_parameter_value
    
def read_config_to_send_email(Patching_type,bucket,S3_directory_name,tagValue,attFileType):
    try:
        SENDER = read_ssm_parameter(SenderEmailId)
        print("SenderEmailId : ", SENDER)
        #SENDER = "rekha@dxc.com"
        CloudOpsTeamEmail_id = read_ssm_parameter(cloudOpsEmailId)
        print("CloudOpsTeamEmail_id : ",CloudOpsTeamEmail_id)
        fileNamesAndEmailIds = {}
        print("Read config to send mail")
        jsonKey = "downtimecontacts"
        fileNamesAndEmailIds = read_jsonfile(bucket, S3_directory_name,jsonKey)

        downtimeContactEmailIDs = CloudOpsTeamEmail_id
        #recipientMailIDs.append("suresh.r@dxc.com;rekha@dxc.com")
                
        recipientMailIDs = []
        for toMailId in downtimeContactEmailIDs.split(";"):
            if toMailId != "":
                recipientMailIDs.append(toMailId)
        
        BODY_TEXT = "Hi Team, \r\n  Patching has been Scheculed for the Instances. \r\nKindly find the Pre Patch compliance scan report for the servers which are scheduled for Patching... Thanks!\r\n Regards,\r\n CloudOps Automation"
        '''BODY_HTML = """\
        <html>
        <head></head>
        <body>
        <p>Hi Team,</p>
        <p>     Kindly find the Pre Patch compliance scan report for the servers which are scheduled for Patching... Thanks!</p><br>
        <p>     Patching has been scheduled for these servers and patching will be started in two days.</p><br>
        <p>Regards,</p>
        <p>CloudOps Automation</p>
        </body>
        </html>
        """
        '''
        
        accoundId,BODY_HTML = create_HTML_Body(Patching_type,tagValue)
        CHARSET = "utf-8"
        attachmentFile = attFileType + "_" + tagValue + ".csv"
        account_name = fetch_account_name()
        SUBJECT = "AWS " + account_name + " PE2EA | "+Patching_type+" Pre Patch Scan Reports " + tagValue     

        fileFullName_S3 = patchScanReportFullFileName + attachmentFile
        fileFullName_Local = local_Folder + attachmentFile
        
        print("\n\n----------------> ",recipientMailIDs)
        print("tagValue : ", tagValue)
        
        print("\nTo Mail ID : ", recipientMailIDs)
        print("File Name : ", attachmentFile)
        
        msg = MIMEMultipart('mixed')
        msg['Subject'] = SUBJECT 
        msg['From'] = SENDER 
        msg['To'] = ','.join(recipientMailIDs)
        
        try:
            download_file_from_S3_bucket(fileFullName_Local,fileFullName_S3)
            #attachmentFile = local_Folder + attachmentFile
            print("attachmentFilePath : ", local_Folder + attachmentFile)
            print("fileFullName_Local : ", fileFullName_Local)
            msg_body = MIMEMultipart('alternative')
            textpart = MIMEText(BODY_TEXT.encode(CHARSET), 'plain', CHARSET)
            htmlpart = MIMEText(BODY_HTML.encode(CHARSET), 'html', CHARSET)
            
            msg_body.attach(textpart)
            msg_body.attach(htmlpart)
            
            os.chdir(local_Folder)
            path = os.path.normpath(f"{os.getcwd()}{os.sep}{attachmentFile}")
            print("Normalized Path:", path)
            att = MIMEApplication(open(path, 'rb').read())
            att.add_header('Content-Disposition','attachment',filename=os.path.basename(path))
            msg.attach(att)
            
            msg.attach(msg_body)

            send_mail(SENDER,recipientMailIDs,msg)
            
        except:
            print(PrintException())
            #sys.exit(PrintException())
    except:
        print(PrintException())


def call_update_dynamodb_lambda_fun(patchJob_id):
    lambda_client = boto3.client('lambda',config=config)
    dynamo_event = {'patchJob_id': patchJob_id,'attribute_name':'pre_patch_scan_status','attribute_value':'completed'}
    response = lambda_client.invoke(
        FunctionName='dxcms-pa-lam-update-dynamodb',
        Payload=json.dumps(dynamo_event)
    )

def lambda_handler(event, context):
    global bucket_name
    global S3_directory_name
    global errorLog_Local_FullFileName
    global local_Folder
    global S3_folder
    global patchScanReportFullFileName
    global region
    global patchJobId
    global patchMonth
    global S3_Folder_Name
    patching_type = event['Patching_Type']
    if patching_type == 'Standard':
        Patching_type = 'STANDARD'
        patching_tag = "PatchInstallOn"
    else:
        patching_tag = "AdhocPatchInstallOn"
        Patching_type = 'ADHOC'
    tagValue = event['PatchInstallOn']
    bucket_name = event['S3_Bucket']
    S3_directory_name = event['S3_directory_name']
    S3_Folder_Name = event['S3_Folder_Name']
    
    patchMonth = S3_directory_name.split("/")[0]
    region = event['region']
    patchJobId = S3_directory_name.split("/")[2]
    
    phase = event['Patch_Phase']
    if phase == "pre-patch":
        patchScanReportFullFileName = S3_Folder_Name + "/" + "PATCHING/" + S3_directory_name + "/PatchScanReports/Pre/"
        File_prefix = "Pre_PatchScanReport"
    elif phase == "post-patch":
        patchScanReportFullFileName = S3_Folder_Name + "/" + "PATCHING/" + S3_directory_name + "/PatchScanReports/Post/"
        File_prefix = "Post_PatchScanReport"
        
    #errorLogFileName = "Error_Logs_Patching_" + tagValue + ".csv"
    errorLogFileName = "Error_Logs_Patching.csv"
    
    local_Folder = "/tmp/"
    errorLog_Local_FullFileName = local_Folder + errorLogFileName
    
    S3_folder = S3_Folder_Name + "/" + 'PATCHING/' + S3_directory_name 
    errorLog_S3_FullFileName =  S3_folder + '/Error Logs/' + errorLogFileName
    
    read_config_to_send_email(Patching_type,bucket_name,S3_directory_name,tagValue,File_prefix)

    call_update_dynamodb_lambda_fun(patchJobId) 
    if os.path.exists(errorLog_Local_FullFileName):
        print("===========================File Exists")
        print("errorLog_Local_FullFileName : ",errorLog_Local_FullFileName)
        print("errorLog_S3_FullFileName : ", errorLog_S3_FullFileName)
        upload_file_into_s3(errorLog_Local_FullFileName,errorLog_S3_FullFileName)
    
    jsonTagValues = {}
    jsonTagValues['Patching_Type'] = patching_type
    jsonTagValues['S3_Bucket'] = event['S3_Bucket']
    jsonTagValues['S3_directory_name'] = S3_directory_name
    jsonTagValues['region'] = region
    jsonTagValues['PatchInstallOn'] = tagValue
    print(jsonTagValues)
    return jsonTagValues

# simple test cases
if __name__ == "__main__":
    event1 = {
  "PatchInstallOn": "WIN_TEST-NOV_21_2021_13_30_4HRS",
  "S3_Bucket": "dxc",
  "S3_directory_name": "NOV_2021/ap-south-1/patchJobId_90963df6-46b9-11ec-b2db-8c8caa2990d1",
  "File_prefix": "Pre_PatchScanReport",
  "Patch_Phase": "pre-patch",
  "S3_Folder_Name" : "test",
  "region":"ap-south-1"
}
 
    lambda_handler(event1, "")
