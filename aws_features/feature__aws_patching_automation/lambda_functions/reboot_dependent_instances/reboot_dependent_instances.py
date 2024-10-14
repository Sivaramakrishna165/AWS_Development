'''
This Lambda function reboots the dependent instances based on the reboot sequence configuration in SSM Parameter and updates the list of servers for which status needs to be checked.
It also sends email if any server has not come up after the number of retries as defined in the WaitTimeRetry SSM parameter.
'''

import json
import boto3
import sys
import os
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))
ssm_para_client = boto3.client('ssm',config=config)

cloudOpsEmailId = os.environ['cloudOpsEmailId']
SenderEmailId = os.environ['SenderEmailId']
retry_status_check_parameter = os.environ['WaitTimeRetry']

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr


def check_instance_status(instance_id):
    try:
        response = ec2_client.describe_instance_status(InstanceIds=[instance_id,])
        Instance_status = response['InstanceStatuses'][0]['InstanceState']['Name']
        print(response['InstanceStatuses'][0]['InstanceState']['Name'])
        if Instance_status:
            instance_reachable = 'Yes'
        return instance_reachable
    except:
        error = PrintException()
        print(error)
        if error:
            instance_reachable = 'No'
        return instance_reachable

 
def reboot_dependent_server(dependent_server_id):
    try:
        server_reachability = check_instance_status(dependent_server_id)
        if server_reachability == 'Yes':
            response = ec2_client.reboot_instances(InstanceIds=[dependent_server_id,])
            print("Rebooted server:",dependent_server_id)
        return response
    except:
        print(PrintException())

def read_email_id_from_ssm_parameter(name):
    try:
        response = ssm_para_client.get_parameter(Name=name,)
        ssm_parameter = response['Parameter']
        parameter_value = ssm_parameter['Value']
        ssm_parameter_value = parameter_value.split(";")
        return ssm_parameter_value
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
                    send_mail(SENDER,recipientMailIDs,msg)
    except:
        print(PrintException())

def email_body_content(InstanceId,dependents_left,patch_type):
    try:
        SENDER = read_email_id_from_ssm_parameter(SenderEmailId)
        SENDER = SENDER[0]
        print("Sender's email_is : ", SENDER)

        recipientMailIDs = read_email_id_from_ssm_parameter(cloudOpsEmailId)
        print("Recipient email_id : ",recipientMailIDs)
        CHARSET = "utf-8"
        SUBJECT = "AWS " +patch_type+ "PE2E Automation | Reboot Issue Notification "
        message = MIMEMultipart("mixed")
        message['Subject'] = SUBJECT 
        message['From'] = SENDER
        message['To'] = ','.join(recipientMailIDs)

        # Create the plain-text and HTML version of your message
        BODY_TEXT = """\
        Hi Team,

        Reboot for the instance is FAILED. Please find the details below.
        
        Error occured on Instance $InstanceId  
        Account ID : $account_id
        Region : $region
        
        Please check the instance. It may be in hung state. Please reboot the further dependents manually.
        $dependents_left
        
        Thanks!

        Regards,
        CloudOps Automation"""

        Instance_id = '<b>Instance : ' + str(InstanceId) + '</b><br>'
        Region_content = '<b>Region : ' + region + '</b><br>'
        Account_content = '<b>Account ID : ' + str(account_id) + '</b><br>'

        BODY_HTML = """ <html>
        <body>
            <p>Hi Team,</p>
            <p>Reboot for the """+patch_type+""" patching Instance is FAILED. Please find the details below.</p><br>
             """
        BODY_HTML = BODY_HTML + """Error occured on 
        """
        BODY_HTML = BODY_HTML + Instance_id
        BODY_HTML = BODY_HTML + Account_content
        BODY_HTML = BODY_HTML + Region_content
        BODY_HTML = BODY_HTML + """<br>Please check the instance. It may be in hung state. Please reboot the further dependents manually.<br>"""
        BODY_HTML = BODY_HTML + str(dependents_left)+"""<p>
                                Thanks! </p>
                                Regards,<br>
                                CloudOps Automation 
                                
                            </body>
                            </html>
                            """
        #print("HTML_Body =======> ", BODY_HTML)
        try:
            msg_body = MIMEMultipart('alternative')
            textpart = MIMEText(BODY_TEXT.encode(CHARSET), 'plain', CHARSET)
            htmlpart = MIMEText(BODY_HTML.encode(CHARSET), 'html', CHARSET)                
            msg_body.attach(textpart)
            msg_body.attach(htmlpart)
            message.attach(msg_body) 
            #print(type(message))          
            send_mail(SENDER,recipientMailIDs,message)
        except:
            print(PrintException())
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

#read ssm parameter for reboot wait time
def read_ssm_parameter_retry(retry_status_check_parameter):
    try:
        ssm_client = boto3.client('ssm',config=config)
        try:
            ssmParameter = ssm_client.get_parameter(Name=retry_status_check_parameter)
            ssm_param_value = json.loads(ssmParameter['Parameter']['Value'])
            retry_limit = ssm_param_value["Retry"]
            return retry_limit
        except:
            print(PrintException())
            print("Error while reading SSM Parameter -",retry_status_check_parameter,"Taking Default value of 10 retries")
            return 10
    except:
        print(PrintException())

        
def lambda_handler(event, context):
    try:
        global region, account_id, ssm_client, ec2_client
        region = event['region']
        S3_Bucket_Name = event['S3_Bucket']
        S3_directory_name = event['S3_directory_name']
        Patching_Type= event['Patching_Type']
        if Patching_Type == 'Adhoc':
            patch_type = 'Adhoc'
        else:
            patch_type = 'Standard'
        patchJobId = S3_directory_name.split("/")[2]
        print("S3_Bucket_Name : ",S3_Bucket_Name)
        print("S3_directory_name : ",S3_directory_name)
        
        account_id = get_aws_account_info()
        ec2_client = boto3.client('ec2',region_name = region,config=config)
        status_check_retries =  event['status_check_retries']
        reboot_sequence = event['Updated_reboot_sequence']
        reboot_status_check = event['Updated_reboot_status_check']
        print("Reboot Sequence Received:", reboot_sequence)
        
        #Reboot the dependents first in the updated list
        dependents_to_reboot = list(reboot_sequence.keys())
        print("Rebooting Dependents:", dependents_to_reboot)
        if len(dependents_to_reboot) >= 1: 
            for dependent in dependents_to_reboot:
                response = reboot_dependent_server(dependent)
                print("Reboot Response for dependent server: ",response)
        
        #Remove server that has not come up in several retries
        updated_status_check_retries = status_check_retries.copy()
        retries_limit = read_ssm_parameter_retry(retry_status_check_parameter)
        for server, retries in status_check_retries.items():
            if retries >= retries_limit:
                print("Please check server:", server,". It may be in hung state. Please reboot further dependents manually.")
                updated_status_check_retries.pop(server)
                dependents_left = reboot_status_check.pop(server)
                print(dependents_left)
                email_body_content(server, dependents_left,patch_type)
        
        event['Updated_reboot_status_check'] = reboot_status_check
        event['status_check_retries'] = updated_status_check_retries 
        
        return event
    except:
        print(PrintException())
        
# sample test cases

if __name__ == "__main__":
    event1 = {
	"PatchInstallOn": "testing-MAY_7_2023_13_5_4HRS_BY_AY",
	"S3_Bucket": "dxcms.patchingautomation.567529657087.us-west-1",
	"S3_directory_name": "MAY_2023/us-west-1/patchJobId_7ec67b43-feae-11ed-b007-57d89e3b79a7",
	"CommandId": "49ec2b9c-822c-409b-8ed7-0c4ccfc7ecee",
	"Status": "pending",
	"app_action": "start",
	"S3_Folder_Name": "patching_reports",
	"region": "us-west-1",
	"Updated_reboot_sequence": {
		"i-0e457c2b98360a88a": [
			"i-08706c4829273c6f5"
		]
	},
	"Wait_time": 120,
	"Updated_reboot_status_check": {},
	"status_check_retries": {}
    }
    lambda_handler(event1, "") 
