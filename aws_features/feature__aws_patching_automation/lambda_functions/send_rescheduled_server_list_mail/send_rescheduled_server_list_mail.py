'''
This Lambda script sends mail to user about the scheduled patching activity along with the server list 
'''

import os
import sys
import boto3
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import json
import csv
from botocore.client import Config
import datetime

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
        Key = fileFullName_S3 
        print("Key : ", Key)
        print("fileFullName_Local : ", fileFullName_Local)
        s3client.download_file(bucket_name, Key, fileFullName_Local)          
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
        cloudWatchRuleName = "Install_Patch_" + tagValue + "_" + region
        
        patchInstallDate_str = str(date) + "-" +  str(month) + "-" + str(year) + "-" + str(hours) + "-" + str(minutes)
        patchStartDate = datetime.datetime.strptime(patchInstallDate_str, '%d-%b-%Y-%H-%M')
        patchEndDate = patchStartDate + datetime.timedelta(hours= +downtimeHoursInt)
    except:
        print(PrintException())
    return patchStartDate,patchEndDate,cloudWatchRuleName,downtimeHours,patchGroup,month

def create_HTML_Body(tagValue,patchJobId,CR):
    try:
        accoundId = get_aws_account_info()
        account_name = fetch_account_name()
        patchStartDate,patchEndDate,cloudWatchRuleName,downtimeHours,patchGroup,month = extract_tagValue(tagValue)
        old_tag = TagMapping[tagValue]
        old_patchJob_id = OldTagValues[old_tag]
        
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
        table = table + "<tr><td>Change Request Number </td><td>" + CR + "</td></tr>"
        table = table + "</table>"

        BODY_HTML = """	<html>
                <head><style>table, th, td { border: 1px solid black;}</style></head>
                <body>
                <p>Hi Team,</p>
                <p style = "font-weight: bold;font-size: 20px;">RESCHEDULED SERVER LIST FOR PATCHING</style></p>
                <p>New Schedule has been created to patch the attached Instances, but currently it is in disabled state. Please follow the below instructions to enable it.</p>
                <p>     """
        BODY_HTML = BODY_HTML + table
        if CR == "N/A":
            BODY_HTML = BODY_HTML +"""</p><br>
                                      <p>Kindly raise a CR for the same.</p>
                                      <p>When the CR gets approved, then proceed to manually enable the above mentioned CloudWatch Rule to enable Patch Schedule.</p>"""
        else:
            old_change = OldChangeRequests[old_patchJob_id]
            BODY_HTML = BODY_HTML + """
                           <p>Once the CR is approved, the above mentioned CloudWatch Rule will be automatically enabled.</p>
                           <p>Update and Close the previous Change Request : """+old_change+"""<p>"""
        
        BODY_HTML = BODY_HTML +"""
                           <p>Regards,</p>
                           <p>CloudOps Automation</p>
                           </body>
                           </html> """
    except:
        print(PrintException())
    return accoundId,BODY_HTML

def filter_json(TagValues,data):
    try:
        filtereddata = {}
        key_list  = list(data.keys())
        for key in key_list:
            for tag in TagValues:
                if tag in key:
                    filtereddata[key] = data[key]
        return filtereddata
    except:
        print(PrintException())

        
def read_jsonfile(S3_Bucket,S3_directory_name,Keyname,TagValues):
    s3client = boto3.client('s3',config=config)
    directory_name = S3_Folder_Name + "/" + "PATCHING"+"/"+ S3_directory_name + "/" + "Patching_config.json"
    response = s3client.get_object(Bucket=S3_Bucket, Key=directory_name)
    content = response['Body']
    jsonObject = json.loads(content.read())
    JsonKey = filter_json(TagValues,jsonObject[Keyname])
    return JsonKey,jsonObject


def send_mail(SENDER,recipientMailIDs,msg):
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
            #print(PrintException())
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

def read_ssm_parameter(name):
    ssm_para_client = boto3.client('ssm',config=config)
    response = ssm_para_client.get_parameter(
        Name=name,
    )
    ssm_parameter = response['Parameter']
    ssm_parameter_value = ssm_parameter['Value']
    return ssm_parameter_value


def read_config_to_send_email(bucket,S3_directory_name,attFileType,TagValues):
    try:
        SENDER = read_ssm_parameter(SenderEmailId)
        print("Sender's email_is : ", SENDER)
        CloudOpsTeamEmail_ids = read_ssm_parameter(cloudOpsEmailId)
        print("CloudOpsTeamEmail_ids : ",CloudOpsTeamEmail_ids)
        fileNamesAndEmailIds = {}
        print("Read config to send mail")
        jsonKey = "downtimecontacts"
        fileNamesAndEmailIds,patchConfigFullData = read_jsonfile(bucket, S3_directory_name,jsonKey,TagValues)
        
        BODY_TEXT = "Hi Team, \r\n  Patching has been Re-Scheculed for the Instances. \r\nKindly find the attached ServerList report for the same for verification. Thanks!\r\n Regards,\r\n CloudOps Automation"
        
        print("Getting Email IDs and datetime")
        for key, value in fileNamesAndEmailIds.items():
            CHARSET = "utf-8"
            tagValue = key
            downtimeContactsEmailIds = value
            print("Tag Value is : ", tagValue)
            patchJobId = patchConfigFullData["patchJobIds"][tagValue]
            try:
                CR = patchConfigFullData["Change_Request"][tagValue]
            except:
                CR = "N/A"
            accoundId,BODY_HTML = create_HTML_Body(tagValue,patchJobId,CR)
            account_name = fetch_account_name()
            print("Account Name : ",account_name)

            attachmentFile = attFileType + "_" + key + ".csv"
            attachmentFile_patchscanreport = "PatchScanReport_" + key + ".csv"
            patchJobId_list = patchJobId.split(" ")
            call_update_dynamodb_lambda_fun(patchJobId_list,'account_name',account_name)
            SUBJECT = "AWS " + account_name + " PE2EA | Patch ServerList " + key 

            fileFullName_S3 = S3_folder + "/" + patchJobId + '/ServersList/' + attachmentFile

            fileFullName_Local = local_Folder + attachmentFile

            fileFullName_S3_patchscan = S3_folder + "/" + patchJobId + '/ServersList/' + attachmentFile_patchscanreport
            fileFullName_Local_patchscan = local_Folder + attachmentFile_patchscanreport
        
            value = CloudOpsTeamEmail_ids

            recipientMailIDs = []
            for toMailId in value.split(";"):
                if toMailId != "":
                    recipientMailIDs.append(toMailId)
            print("\nTo Mail ID : ", recipientMailIDs)
            print("File Name : ", attachmentFile)
            
            msg = MIMEMultipart('mixed')
            msg['Subject'] = SUBJECT 
            msg['From'] = SENDER 
            msg['To'] = ','.join(recipientMailIDs)
            
            try:
                download_file_from_S3_bucket(fileFullName_Local,fileFullName_S3)
                attachmentFile = local_Folder + attachmentFile
                print("attachmentFile : ", attachmentFile)
                print("fileFullName_Local : ", fileFullName_Local)

                download_file_from_S3_bucket(fileFullName_Local_patchscan,fileFullName_S3_patchscan)
                attachmentFile_patchscanreport = local_Folder + attachmentFile_patchscanreport
                print("attachmentFile for Patch scan : ", attachmentFile_patchscanreport)
                print("fileFullName_Local for Patch scan : ", fileFullName_Local_patchscan)

                msg_body = MIMEMultipart('alternative')
                textpart = MIMEText(BODY_TEXT.encode(CHARSET), 'plain', CHARSET)
                htmlpart = MIMEText(BODY_HTML.encode(CHARSET), 'html', CHARSET)
                
                msg_body.attach(textpart)
                msg_body.attach(htmlpart)

                att = MIMEApplication(open(attachmentFile, 'rb').read())
                att.add_header('Content-Disposition','attachment',filename=os.path.basename(attachmentFile))

                att_patchscan = MIMEApplication(open(attachmentFile_patchscanreport, 'rb').read())
                att_patchscan.add_header('Content-Disposition','attachment',filename=os.path.basename(attachmentFile_patchscanreport))

                msg.attach(msg_body)
                msg.attach(att)
                msg.attach(att_patchscan)

                send_mail(SENDER,recipientMailIDs,msg)
                print("Mail has been sent......")
                
            except:
                print(PrintException())
                #sys.exit(PrintException())
    except:
        print(PrintException())


def call_update_dynamodb_lambda_fun(patchJob_ids,attribute_name,attribute_value):
    lambda_client = boto3.client('lambda',config=config)
    for i in range(len(patchJob_ids)):
        dynamo_event = {'patchJob_id': patchJob_ids[i],'attribute_name':attribute_name,'attribute_value':attribute_value}
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
    global region
    global patchMonth
    global S3_Folder_Name
    global OldChangeRequests
    global TagMapping
    global OldTagValues
    
    bucket_name = event['S3_Bucket']
    S3_directory_name = event['S3_directory_name']
    S3_Folder_Name = event['S3_Folder_Name']
    TagValues = event['TagValues']
    patchMonth = S3_directory_name.split("/")[0]
    region = event['region']
    OldTagValues = event['OldTagValues']
    TagMapping = event['TagMapping']
    if event['Snow_Integration_Status'] == 'ON':
        OldChangeRequests = event['OldChangeRequests']
    
    errorLogFileName = "Error_Logs_Patching.csv"
    
    local_Folder = "/tmp/"
    errorLog_Local_FullFileName = local_Folder + errorLogFileName
    
    S3_folder = S3_Folder_Name + "/" + 'PATCHING/' + S3_directory_name 
    errorLog_S3_FullFileName =  S3_folder + '/Error Logs/' + errorLogFileName 
    
    if (IsObjectExists(errorLog_S3_FullFileName)):
        download_file_from_S3_bucket(errorLog_Local_FullFileName,errorLog_S3_FullFileName)  
    
    read_config_to_send_email(bucket_name,S3_directory_name,"PatchServerList",TagValues)
    Keyname = 'patchJobIds'
    patchJob_Ids, data = read_jsonfile(bucket_name,S3_directory_name,Keyname,TagValues)
    patchJob_Id = list(patchJob_Ids.values())
    print("Patch_Job_Ids ==== ",patchJob_Id)
    call_update_dynamodb_lambda_fun(patchJob_Id,'patch_job_status','scheduled')
    
    if os.path.exists(errorLog_Local_FullFileName):
        print("===========================File Exists")
        print("errorLog_Local_FullFileName : ",errorLog_Local_FullFileName)
        print("errorLog_S3_FullFileName : ", errorLog_S3_FullFileName)
        upload_file_into_s3(errorLog_Local_FullFileName,errorLog_S3_FullFileName)
    
    jsonTagValues = {}
    jsonTagValues['S3_Bucket'] = event['S3_Bucket']
    jsonTagValues['S3_directory_name'] = S3_directory_name
    jsonTagValues['S3_Folder_Name'] = S3_Folder_Name
    jsonTagValues['region'] = region
    print(jsonTagValues)
    return jsonTagValues

# simple test cases
if __name__ == "__main__":
    event1 = {
  "OldTagValues": {
    "DEV-JUN_30_2023_15_0_4HRS": "patchJobId_fa844949-1a3d-11ee-9a9b-d74ac618a13f",
    "PROD-JUN_30_2023_15_0_3HRS": "patchJobId_fba11e3d-1a3d-11ee-b948-d74ac618a13f"
  },
  "TagValues": [
    "DEV-JUN_30_2023_10_0_4HRS",
    "PROD-JUN_30_2023_10_0_3HRS"
  ],
	"S3_Bucket": "dxcms.patchingautomation.567529657087.eu-west-3",
	"S3_directory_name": "JUN_2023/eu-west-3",
    "File_prefix": "PatchServerList",
	"S3_Folder_Name": "patching_reports",
	"region": "eu-west-3",
    "Snow_Integration_Status": "ON",
    "OldChangeRequests" : {
    "patchJobId_fa844949-1a3d-11ee-9a9b-d74ac618a13f" : "CHG012345",
    "patchJobId_fba11e3d-1a3d-11ee-b948-d74ac618a13f" : "CHG023456"
    }
}
    lambda_handler(event1, "")
