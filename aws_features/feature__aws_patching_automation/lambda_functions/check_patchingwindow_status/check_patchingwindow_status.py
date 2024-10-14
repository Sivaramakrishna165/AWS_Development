'''
This lambda script checks the Patching window status. 
If the Patching window is missed, it will inovke cleanup 
lambda functon dxcms-pa-lam-cwr-tag-cleanup and it will also 
sends an email notification of cleanup resources that were created during the schedule phase.

sample event 1:-
{
  "S3_Bucket": "dxcms.patchingautomation.567529657087.ap-southeast-2",
  "S3_directory_name": "JUN_2023/ap-southeast-2",
  "S3_Folder_Name": "patching_reports",
  "region": "ap-southeast-2",
  "Tag_Value": "PKT-JUN_27_2023_4_0_4HRS",
  "Trigger_Rule_Name": "Patching_Window_Check_PKT-JUN_27_2023_4_0_4HRS"
}
sample event 2:-
{
  "S3_Bucket": "dxcms.patchingautomation.567529657087.ap-southeast-2",
  "S3_directory_name": "JUN_2023/ap-southeast-2",
  "S3_Folder_Name": "patching_reports",
  "region": "ap-southeast-2",
  "Tag_Value": "PKT-JUN_27_2023_4_0_4HRS",
  "Trigger_Rule_Name": "SNOW_CR_Status_Check_PKT-JUN_27_2023_4_0_4HRS"
}

'''

import boto3
import json
import sys
import os
import base64
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from botocore.client import Config
from botocore.retries import bucket
from botocore.config import Config
from datetime import datetime

config=Config(retries=dict(max_attempts=10,mode='standard'))

cloudOpsEmailId = os.environ['cloudOpsEmailId']
# cloudOpsEmailId = '/DXC/Notification/DXCNotifyEmail'
SenderEmailId = os.environ['SenderEmailId']
# # SenderEmailId = '/DXC/PatchingAutomation/Sender_Email_ID'
cleanup_lambda_name =os.environ['cleanup_lambda_name']


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


def get_patching_window_status(install_patch_rule_name):
    try:
        event_client = boto3.client('events',config=config)
        response = event_client.describe_rule(Name=install_patch_rule_name)
        rschedule = response['ScheduleExpression'].replace('cron(','').replace(')','').split(' ')
        rmins,rhours,rday,rmonth,ryear = rschedule[0], rschedule[1],rschedule[2],rschedule[3],rschedule[5]
        if int(rmins)<10:
            rtime = rhours+':0'+rmins
        else:
            rtime = rhours+':'+rmins
        print(response['Name'],response['State'],rtime,rday+'-'+rmonth+'-'+ryear)
        schedule_str = rmonth+' '+rday+' '+ryear+' '+rhours+':'+rmins
        datetime_schedule = datetime.strptime(schedule_str, '%b %d %Y %H:%M')
        utc_time = datetime.utcnow()
        if utc_time < datetime_schedule:
            pw_status = 'upcoming'
        else:
            pw_status = 'missed'
        print(pw_status)
    except:
        print(PrintException())
    return pw_status


def get_missed_message(tagvalue,install_patch_rule_name,patch_scan_rule_name,perform_pretask_rule_name,trigger_rule_name):
    try:
        current_month = datetime.now().strftime("%b").upper()
        current_year = datetime.now().strftime("%Y")
        result = current_month + "_" + current_year
        other_rule = trigger_rule_name.split(tagvalue)[0]
        table = "<table>"
        table = table + "<tr><td>PatchInstallOn Tags </td><td> "+tagvalue+"*"+"</td></tr>"
        table = table + "<tr><td>Install_Patch_ CW Rule </td><td> "+install_patch_rule_name+"</td></tr>"
        table = table + "<tr><td>PatchScan_ CW Rule </td><td> "+patch_scan_rule_name+ "</td></tr>"
        table = table + "<tr><td>Peform_PreTask_ CW Rule </td><td> "+perform_pretask_rule_name+"</td></tr>"
        table = table + "<tr><td>"+other_rule+" CW Rule </td><td> "+trigger_rule_name+"</td></tr>"
        table = table + "</table>"
        table_text = table.replace("<table>","\n").replace("<tr><td>","\n").replace("</td><td>",":").replace("</td></tr>","").replace("</table>","\n")
        
        msg_text = """\Please note that the Patching Window for this month was missed. 
        Below resources will be deleted by automation that were created for the Patching activity.
        For more details on the affected resources refer S3 bucket path (patching_reports/PATCHING/"""+result+"""/"""+region+"""/Patching-Windows-missed/
        """+table_text
        
        msg_html = """<p>Please note that the Patching Window for this month was missed.<br/>Below resources will be deleted by automation that were created for the Patching activity.
        <br/>For more details on the affected resources refer S3 bucket path (patching_reports/PATCHING/"""+result+"""/"""+region+"""/Patching-Windows-missed/
        </p>"""+table
    except:
        print(PrintException())
    return msg_text, msg_html

def create_HTML_Body(CloudWatchRule,region,msg_html):
    try:
                
        table = "<table>"
        table = table + "<tr><td>Account ID </td><td>" + str(accoundId) + "</td></tr>"
        table = table + "<tr><td>Account Name </td><td>" + str(account_name) + "</td></tr>"
        table = table + "<tr><td>Region </td><td>" + region + "</td></tr>"
        table = table + "<tr><td>CloudWatch Rule Name </td><td>" + CloudWatchRule + "</td></tr>"
        table = table + "</table>"

        BODY_HTML = """<html>
                    <head><style>table, th, td { border: 1px solid black;}</style></head>
                    <body>
                    <p>Hi Team,</p>
                    <p style = "font-weight: bold;font-size: 20px;color:red;">PATCHING WINDOW MISSED</style></p>
                    <p>The patching schedule was defined as below for the account mentioned. </p>
                    <p>     """

        BODY_HTML = BODY_HTML + table
        BODY_HTML = BODY_HTML + msg_html
        BODY_HTML = BODY_HTML + """ </p>
                           <p>Perform manual patching of the instances for which the patching schedule was not approved/missed once Change Request is approved.</p>
                           <p>Thanks!</p>
                           <p>Regards,</p>
                           <p>CloudOps Automation</p>
                           </body>
                           </html> """
    except:
        print(PrintException())
    return BODY_HTML, table

def email_body_content(Tagvalue,CloudWatchRule,region,msg_text,msg_html):
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

        CHARSET = "utf-8"
        SUBJECT = "AWS "+ account_name + " PE2EA | PATCHING WINDOW MISSED " + Tagvalue
        message = MIMEMultipart("mixed")
        message['Subject'] = SUBJECT 
        message['From'] = SENDER
        message['To'] = ','.join(recipientMailIDs)

        # Create the plain-text and HTML version of your message
        BODY_HTML, table = create_HTML_Body(CloudWatchRule,region,msg_html)
        table_text = table.replace("<table>","\n").replace("<tr><td>","\n").replace("</td><td>",":").replace("</td></tr>","").replace("</table>","\n")
        
        BODY_TEXT = """\
            Hi Team,

            The patching schedule was defined as below for the account mentioned.  
            
            """+table_text+"""
            """+msg_text+"""
            Perform manual patching of the instances for which the patching schedule was not approved/missed once Change Request is approved.
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
    global S3_Bucket, S3_Folder_Name, region, tagvalue, accoundId, account_name
    print("Received event is ",event)
    region = event['region']
    S3_Bucket = event['S3_Bucket']
    S3_directory_name = event['S3_directory_name']
    S3_Folder_Name = event['S3_Folder_Name']
    tagvalue = event['Tag_Value']
    trigger_rule = event['Trigger_Rule_Name']
    accoundId,account_name = get_aws_account_info()
    
    CWrules = ["Install_Patch_" + tagvalue + "_" + region, "PatchScan_" + tagvalue + "_" + region , "Peform_PreTask_" + tagvalue + "_" + region]
    message_text, message_html = "", ""
    patching_window_status = get_patching_window_status(CWrules[0])
    if patching_window_status == 'missed':
        print("Patching Window Status :",patching_window_status)
        message_text, message_html = get_missed_message(tagvalue,CWrules[0],CWrules[1],CWrules[2],trigger_rule)
        email_body_content(tagvalue,CWrules[0],region,message_text,message_html)
        lambda_client = boto3.client('lambda',config=config)
        payload = json.dumps(event)
        invocation = {
            'FunctionName': cleanup_lambda_name,
            'InvocationType': 'Event',
            'Payload': payload
        }
        response = lambda_client.invoke(**invocation)
        print(f"Invocation response: {response['StatusCode']}")
        print(f"Invocation payload: {response['Payload'].read().decode('utf-8')}")
        
        # Return a response from another Lambda function 
        return {
            'statusCode': 200,
            'body': 'Lambda function A executed successfully!'
        }
        
    else:
        print("Patching Window Status :",patching_window_status)

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