'''
This lambda script checks the Change request whether it is in scheduled phase and it enables the Install_patch cloud watch event rule.
If the Change Request is not approved before the patching schedule, it sends notification for the same.
'''

import boto3
import requests 
from requests.auth import HTTPBasicAuth 
import json
import sys
import os
import base64
from botocore.exceptions import ClientError
from requests.models import encode_multipart_formdata
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from botocore.client import Config
from botocore.retries import bucket
import csv
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

cloudOpsEmailId = os.environ['cloudOpsEmailId']
SenderEmailId = os.environ['SenderEmailId']
secret_manager_name = os.environ['Secret_Name']
 


def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

def read_ssm_parameter(name):
    ssm_para_client = boto3.client('ssm',config=config)
    response = ssm_para_client.get_parameter(
        Name=name 
    )
    ssm_parameter = response['Parameter']
    ssm_parameter_value = ssm_parameter['Value']
    return ssm_parameter_value

def get_secret():
    secret_name = secret_manager_name
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager'
    )
    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    return secret


def read_data_from_config_file(S3_Bucket,S3_directory_name):
    Keyname1 = 'Change_Request'
    Keyname2 = 'executePatchInstallation'
    Keyname3 = 'patchJobIds'
    s3client = boto3.client('s3',config=config)
    directory_name = S3_Folder_Name + "/" + "PATCHING" + "/" + S3_directory_name + "/" + "Patching_config.json"
    response = s3client.get_object(Bucket=S3_Bucket, Key=directory_name)
    content = response['Body']
    jsonObject = json.loads(content.read())
    Change_Request = jsonObject[Keyname1]
    Install_patches = jsonObject[Keyname2] 
    patchJobIds = jsonObject[Keyname3]
    Install_patches_CW, schedule_time = zip(*Install_patches.items())
    return Install_patches_CW,patchJobIds, Change_Request

def fetch_CR_status(cr_number,secret):    
    # prod_url = read_ssm_parameter(Snow_url)
    # set the credential
    credential = json.loads(secret)
    username = credential['snowuser']
    password = credential['snowpassword']
    Snow_url = credential['snowhost']
    # url = "https://csctest.service-now.com/api/sn_chg_rest/change?sysparm_query=number=CHG0121830"
    url = Snow_url + "/api/sn_chg_rest/change?sysparm_query=number=" + cr_number
    # Set the proper headers
    headers = {"Accept":"application/json"} 
    # Make the HTTP request
    response = requests.get(str(url), auth=(username, password), headers=headers)
    # Check for HTTP codes other than 200
    if response.status_code != 200: 
        print('Status:', response.status_code, 'Headers:', response.headers, 'Error Response:', response.content)
        exit()
    print(response.content.decode('utf-8'))
    cr_details = response.content.decode('utf-8')
    cr_details_json = json.loads(cr_details)
    #print("cr_details_json : ",cr_details_json)
    print("=================================================================================")
    # Company details
    company_display_value = cr_details_json["result"][0]['company']['display_value']
    print("company_display_value : ",company_display_value)
    company_value = cr_details_json["result"][0]['company']['value']
    print("company_value : ",company_value)
    print("=================================================================================")
    # Assignment Group Details
    assignment_group_display_value = cr_details_json["result"][0]['assignment_group']['display_value']
    print("assignment_group_display_value : ",assignment_group_display_value)
    assignment_group_value = cr_details_json["result"][0]['assignment_group']['value']
    print("assignment_group_value : ",assignment_group_value)
    print("=================================================================================")
    # Sys id details
    sys_id_display_value = cr_details_json["result"][0]['sys_id']['display_value']
    print("sys_id_display_value : ",sys_id_display_value)
    sys_id_value = cr_details_json["result"][0]['sys_id']['value']
    print("sys_id_value : ",sys_id_value)
    print("===================================================================================")
    # CR state
    Change_request_state = cr_details_json["result"][0]['state']['display_value']
    print("Change_request_state : ",Change_request_state)
    print("sys_id_value : ",sys_id_value)
    return company_value,assignment_group_value,sys_id_value,Change_request_state


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


def create_HTML_Body(status,change_request,CloudWatchRules,region,patch_type):
    try:
        accoundId = get_aws_account_info()
        account_name = fetch_account_name()
        table = "<table>"
        table = table + "<tr><td>Change Request </td><td>" + str(change_request) + "</td></tr>"
        table = table + "<tr><td>Account ID </td><td>" + str(accoundId) + "</td></tr>"
        table = table + "<tr><td>Account Name </td><td>" + str(account_name) + "</td></tr>"
        table = table + "<tr><td>Region </td><td>" + region + "</td></tr>"
        table = table + "<tr><td>CloudWatch Rule Name </td><td>" + CloudWatchRules + "</td></tr>"
        table = table + "</table>"
        BODY_HTML = ''
        if status == 'Approved':
            BODY_HTML = """	<html>
                    <head><style>table, th, td { border: 1px solid black;}</style></head>
                    <body>
                    <p>Hi Team,</p>
                    <p style = "font-weight: bold;font-size: 20px;">CR APPROVED FOR """+patch_type+""" PATCHING</style></p>
                    <p>     Change Request has been approved and patching schedule has been enabled by automation. Kindly look for the mails/notifications for further updates. <//p>
            
                    <p>Please find the information for the Change Request below.</p>
                    <p>     """
        else:
            BODY_HTML = """	<html>
                    <head><style>table, th, td { border: 1px solid black;}</style></head>
                    <body>
                    <p>Hi Team,</p>
                    <p style = "font-weight: bold;font-size: 20px;">CR NOT APPROVED FOR """+patch_type+""" PATCHING</style></p>
                    <p>     Change Request has not been approved and patching schedule has not been enabled by automation. Kindly look for the mails/notifications for further updates. <//p>
            
                    <p>Please find the information for the Change Request below.</p>
                    <p>     """

        BODY_HTML = BODY_HTML + table
        BODY_HTML = BODY_HTML + """ <br>Please ensure the Change Request is approved before the Patching Schedule.</p><br>
                           <p>Thanks!</p>
                           <p>Regards,</p>
                           <p>CloudOps Automation</p>
                           </body>
                           </html> """
    except:
        print(PrintException())
    return BODY_HTML, table

#S3_directory_name,Tagvalues[i],CR_numbers[i],CloudWatchRules[i],region  change_request,CloudWatchRules,region
def email_body_content(status,S3_directory_name,Tagvalues,CR_numbers,CloudWatchRules,region,patch_type):
    try:
        SENDER = read_ssm_parameter(SenderEmailId)
        print("Sender's email_is : ", SENDER)
        #Sender = "abc@dxc.com"
        recipientMailID = read_ssm_parameter(cloudOpsEmailId)
        print("Recipient email_id : ",recipientMailID)

        value = recipientMailID

        recipientMailIDs = []
        for toMailId in value.split(";"):
            if toMailId != "":
                recipientMailIDs.append(toMailId)
        print("\nTo Mail ID : ", recipientMailIDs)

        account_name = fetch_account_name()
        CHARSET = "utf-8"
        SUBJECT = "AWS "+ account_name +" "+ patch_type + " PE2EA | CR# " + CR_numbers + " "+status+" "+ Tagvalues
        message = MIMEMultipart("mixed")
        message['Subject'] = SUBJECT 
        message['From'] = SENDER
        message['To'] = ','.join(recipientMailIDs)

        # Create the plain-text and HTML version of your message
        BODY_TEXT =''
        
        BODY_HTML, table = create_HTML_Body(status,CR_numbers,CloudWatchRules,region,patch_type)
        table_text = table.replace("<table>","\n").replace("<tr><td>","\n").replace("</td><td>",":").replace("</td></tr>","").replace("</table>","\n")
        
        if status == 'Approved':
            BODY_TEXT = """\
            Hi Team,

            Change Request has been approved and Patching Activity has been scheduled by automation. 
            Kindly look for the mails/notifications for further updates. 
            
            Please find the information for the Change Request below.
            """+table_text+"""
            
            Thanks!

            Regards,
            CloudOps Automation"""
        else:
            BODY_TEXT = """\
            Hi Team,

            Change Request has not been approved and Patching Activity has not been scheduled by automation. 
            Kindly look for the mails/notifications for further updates. 
            
            Please find the information for the Change Request below.
            """+table_text+"""
            Please ensure the Change Request is approved before the Patching Schedule.
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
            
            send_mail(SENDER,recipientMailIDs,message)
        except:
            print(PrintException())
    except:
        print(PrintException())

def call_update_dynamodb_lambda_function(patchJob_ids,attribute_name,attribute_value):
    lambda_client = boto3.client('lambda',config=config)
    for i in range(len(patchJob_ids)):
        dynamo_event = {'patchJob_id': patchJob_ids,'attribute_name':attribute_name,'attribute_value':attribute_value}
        response = lambda_client.invoke(
            FunctionName='dxcms-pa-lam-update-dynamodb',
            Payload=json.dumps(dynamo_event)
        )


def lambda_handler(event, context):
    global S3_Bucket,S3_Folder_Name,region,S3_directory_name
    print("Received event is ",event)
    region = event['region']
    events_client = boto3.client('events',config=config)
    S3_Bucket = event['S3_Bucket']
    S3_directory_name = event["S3_directory_name"]
    S3_Folder_Name = event['S3_Folder_Name']
    tagvalue = event['Tag_Value']
    Patching_Type= event['Patching_Type']
    if Patching_Type == 'Adhoc':
        patch_type = 'ADHOC'
    else:
        patch_type = 'STANDARD'
    secrets = get_secret()
    
    CloudWatchRules, patch_job_ids, Change_Requests = read_data_from_config_file(S3_Bucket,S3_directory_name)
    
    for tag_key,CR_number in Change_Requests.items():
        if tag_key == tagvalue:
            cr_company_value, assignment_grp_value, sys_id, CR_Status= fetch_CR_status(CR_number,secrets)
            print("CR_STATUS : ",CR_Status)
            if CR_Status == "Scheduled":
                status = 'Approved'
                call_update_dynamodb_lambda_function(patch_job_ids[tagvalue],attribute_name = "change_request_status",attribute_value = "Scheduled")
                for rule_name in CloudWatchRules:
                    if tagvalue in rule_name:
                        install_patch_rule_name = rule_name + "_" + region
                        print(install_patch_rule_name)
                        response = events_client.enable_rule(Name = install_patch_rule_name)
                        email_body_content(status,S3_directory_name,tagvalue,CR_number,install_patch_rule_name,region,patch_type)
            else:
                status = 'Not Approved'
                for rule_name in CloudWatchRules:
                    if tagvalue in rule_name:
                        install_patch_rule_name = rule_name + "_" + region
                        print(install_patch_rule_name)
                        email_body_content(status,S3_directory_name,tagvalue,CR_number,install_patch_rule_name,region,patch_type)


event1 = {
  "S3_Bucket": "dxcms.patchingautomation.567529657087.eu-west-3",
  "S3_directory_name": "MAR_2023/eu-west-3",
  "S3_Folder_Name": "patching_reports",
  "region": "eu-west-3",
  "Tag_Value": "UAT-MAR_25_2023_11_5_3HRS",
  "Trigger_Rule_Name": "SNOW_CR_Status_Check_UAT-MAR_25_2023_11_5_3HRS"
}

    
if __name__ == "__main__":
    lambda_handler(event1,"")


