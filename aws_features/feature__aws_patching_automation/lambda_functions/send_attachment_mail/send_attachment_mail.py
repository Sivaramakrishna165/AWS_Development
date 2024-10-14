'''
This lambda script is used to attach the reports such as server list, patch scan reports, etc and communicate to the users
'''

import os,sys
import boto3
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import json,csv
from botocore.client import Config
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

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
    s3client = boto3.client('s3',config=config)
    directory_name = "PATCHING"+"/"+ S3_directory_name + "/" + "Patching_config.json"
    response = s3client.get_object(Bucket=S3_Bucket, Key=directory_name)
    content = response['Body']
    jsonObject = json.loads(content.read())
    JsonKey = jsonObject[Keyname]
    return JsonKey


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
    
def read_config_to_send_email(bucket,S3_directory_name,attFileType):
    try:
        SENDER = "rekha@dxc.com"
        fileNamesAndEmailIds = {}
        print("Read config to send mail")
        jsonKey = "downtimecontacts"
        fileNamesAndEmailIds = read_jsonfile(bucket, S3_directory_name,jsonKey)
        
        BODY_TEXT = "Hello,\r\nPlease see the attached file."
        BODY_HTML = """\
        <html>
        <head></head>
        <body>
        <h1>Hello!</h1>
        <p>Please see the attached file.</p>
        </body>
        </html>
        """
        
        for key, value in fileNamesAndEmailIds.items():
            CHARSET = "utf-8"
            if attFileType == "PatchServerList":
                #attachmentFile = key + ".csv"
                attachmentFile = attFileType + "_" + key + ".csv"
                SUBJECT = "AWS | " + attachmentFile
                #fileFullName_S3 = S3_folder + '/ServersList/' + 'PatchServerList_' + attachmentFile
                fileFullName_S3 = S3_folder + '/ServersList/' + attachmentFile
                #fileFullName_Local = local_Folder + 'PatchServerList_' + attachmentFile
                fileFullName_Local = local_Folder + attachmentFile
            elif attFileType == "PatchScanReport":
                attachmentFile = attFileType + "_" + key + ".csv"
                SUBJECT = "AWS | " + attachmentFile
                fileFullName_S3 = S3_folder + '/PatchScanReports/' + attachmentFile
                fileFullName_Local = local_Folder + attachmentFile
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
                msg_body = MIMEMultipart('alternative')
                textpart = MIMEText(BODY_TEXT.encode(CHARSET), 'plain', CHARSET)
                htmlpart = MIMEText(BODY_HTML.encode(CHARSET), 'html', CHARSET)
                
                msg_body.attach(textpart)
                msg_body.attach(htmlpart)

                att = MIMEApplication(open(attachmentFile, 'rb').read())
                #print("ATTACHMENT : ",att)
                att.add_header('Content-Disposition','attachment',filename=os.path.basename(attachmentFile))
                msg.attach(msg_body)
                msg.attach(att)
            
                send_mail(SENDER,recipientMailIDs,msg)
                
            except:
                sys.exit(PrintException())
    except:
        PrintException()
            
def lambda_handler(event, context):
    global bucket_name
    global S3_directory_name
    global errorLog_Local_FullFileName
    global local_Folder
    global S3_folder
    global region

    region = event['region']
    bucket_name = event['S3_Bucket']
    S3_directory_name = event['S3_directory_name']
        
    #errorLogFileName = "Error_Logs_Patching_" + tagValue + ".csv"
    errorLogFileName = "Error_Logs_Patching.csv"
    
    #local_Folder = "C:\\temp\\"
    local_Folder = "/tmp/"
    errorLog_Local_FullFileName = local_Folder + errorLogFileName
    
    S3_folder = 'PATCHING/' + S3_directory_name 
    errorLog_S3_FullFileName =  S3_folder + '/Error Logs/' + errorLogFileName 
    
    if (IsObjectExists(errorLog_S3_FullFileName)):
        download_file_from_S3_bucket(errorLog_Local_FullFileName,errorLog_S3_FullFileName)  
                
    if event['File_prefix'] == "PatchServerList":
        read_config_to_send_email(bucket_name,S3_directory_name,"PatchServerList")
    elif event['File_prefix'] == "PatchScanReport":
        read_config_to_send_email(bucket_name,S3_directory_name,"PatchScanReport")
        
    if os.path.exists(errorLog_Local_FullFileName):
        print("===========================File Exists")
        print("errorLog_Local_FullFileName : ",errorLog_Local_FullFileName)
        print("errorLog_S3_FullFileName : ", errorLog_S3_FullFileName)
        upload_file_into_s3(errorLog_Local_FullFileName,errorLog_S3_FullFileName)
    
    jsonTagValues = {}
    jsonTagValues['S3_Bucket'] = event['S3_Bucket']
    jsonTagValues['S3_directory_name'] = S3_directory_name
    jsonTagValues['region'] = region
    print(jsonTagValues)
    return jsonTagValues

# simple test cases
if __name__ == "__main__":
    event1 = {"S3_Bucket": "dxc","S3_directory_name": "MAY_2021","File_prefix": "PatchServerList","region":"ap-south-1"}   
    lambda_handler(event1, "")
