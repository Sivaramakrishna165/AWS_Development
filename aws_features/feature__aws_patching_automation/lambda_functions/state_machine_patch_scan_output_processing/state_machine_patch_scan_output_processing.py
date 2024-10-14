'''
This lambda script is used to process the step funciton output for the error and communicate to the user
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

def email_body_content(Patching_type,S3_directory_name,tagValue,Cause,Execution,StateMachine_Name,StateMachine_Id,State):
    try:
        split_S3_directory_name = S3_directory_name.split("/")
        Region = split_S3_directory_name[1]
        print("Region ==> ",Region)
        #patchJobId = split_S3_directory_name[2]
        print("split_S3_directory_name ==> ",split_S3_directory_name)
        Execution_data = Execution.split(":")
        Account_id = Execution_data[4]
        print("Account_id == > ",Account_id)
        State = State['Name']
        print("State ==> ", State)
        Execution_id = Execution_data[7]
        SENDER = read_ssm_parameter(SenderEmailId)
        SENDER = SENDER[0]
        print("Sender's email_is : ", SENDER)
        #Sender = "rekha@dxc.com"
        recipientMailIDs = read_ssm_parameter(cloudOpsEmailId)
        print("Recipient email_id : ",recipientMailIDs)
        CHARSET = "utf-8"
        SUBJECT = "ERROR - AWS " + Account_id + " PE2EA | "+ Patching_type +"Patching Step Function Failed  " + tagValue
        message = MIMEMultipart("mixed")
        message['Subject'] = SUBJECT 
        message['From'] = SENDER
        message['To'] = ','.join(recipientMailIDs)

        # Create the plain-text and HTML version of your message
        BODY_TEXT = """\
        Hi Team,

        Patching Automation is FAILED on State.. Please find the details in below.
        Error occured on StateMachine $StateMachine_Name / 
        State Machine Arn - $StateMachine_Id / 
        Execution_Id - $Execution
        
        Patch Job ID : $patchJobId$
        Account : $Account_id
        Region : $Region
        Thanks!

        Regards,
        CloudOps Automation"""

        table = "<table>"
        #table = table + "<tr><td>Patch Id</td><td>" + str(patchJobId) + "</td></tr>"
        table = table + "<tr><td>Account ID </td><td>" + str(Account_id) + "</td></tr>"
        table = table + "<tr><td>Region </td><td>" + str(Region) + "</td></tr>"
        table = table + "<tr><td>Tag Value </td><td>" + str(tagValue) + "</td></tr>"
        table = table + "<tr><td>State Machine </td><td>" + str(StateMachine_Name) + "</td></tr>"
        table = table + "<tr><td>State Machine ID </td><td>" + str(StateMachine_Id) + "</td></tr>"
        table = table + "<tr><td>Error occured at : </td><td>" + str(State) + "</td></tr>"
        table = table + "<tr><td>Execution_Id : </td><td>" + str(Execution_id) + "</td></tr>"

        BODY_HTML = """ <html>
            <head><style>table, th, td { border: 1px solid black;}</style></head>
            <body>
            <p style = "font-weight: bold;font-size: 20px;color:red;">PATCH STEP FUNCTION FAILED</style></p>
            <p>Hi Team,</p>
            <p>""" + Patching_type + """ Patching Automation is FAILED for """ + tagValue + """ . Kindly find the details in below.
             """
        BODY_HTML = BODY_HTML + table + "</table>"
        
        BODY_HTML = BODY_HTML + """
                                <p> Thanks! </p>
                                <p> Regards, </p>
                                <p> CloudOps Automation </p>
                                
                            </body>
                            </html>
                            """
        #print("HTML_Body =======> ", BODY_HTML)
        #BODY_HTML = MIMEText(BODY_HTML, "html")
        #BODY_TEXT = MIMEText(BODY_TEXT, "plain")
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

def lambda_handler(event, context):
    output_with_error_cause = {}
    output = {}
    print("Input to the lambda function : ",event)
    TagName = event[0]['TagName']
    if TagName == 'Downtime Window':
        patching_type = "Standard"
    else:
        patching_type = "Adhoc"
    tagValue = event[1]['Input']["TagValues"]
    S3_Bucket = event[1]['Input']['S3_Bucket']
    S3_directory_name = event[1]['Input']['S3_directory_name']
    try:
        if event[0]['Cause']:
            Cause = event[0]['Cause']
            print("Cause =====> ",Cause)
            Execution = event[1]["Execution"]
            print("Execution ====> ",Execution)
            State = event[0]['State']
            print("State ==> ",State)
            StateMachine_Name = event[1]['StateMachine']['Name']
            StateMachine_Id = event[1]['StateMachine']['Id']
            output["Cause"] = Cause
            output['TagName'] = TagName
            output["TagValues"] = tagValue
            output["S3_Bucket"] = S3_Bucket
            output["S3_directory_name"] = S3_directory_name
            output["Step Function Execution_id"] = Execution
            output["StateMachine"] = StateMachine_Name
            print("output_with_error_cause ======> ",output)
            email_body_content(patching_type,S3_directory_name,tagValue,Cause,Execution,StateMachine_Name,StateMachine_Id,State)
        return output
        #print("output_with_error_cause ======> ",output_with_error_cause)
    except:
        output = event[0]
        return output
        print("output =======> ",output)
    
# simple test cases
event1 = [
  {
    "ErrorMessageFrom": "generate_PatchScan_Report Function",
    "State": {
      "Name": "generate_PatchScan_Report_error",
      "EnteredTime": "2021-06-02T08:28:25.924Z"
    },
    "Cause": "{\"errorMessage\": \"'status'\", \"errorType\": \"KeyError\", \"stackTrace\": [\"  File \\\"/var/task/lambda_function.py\\\", line 421, in lambda_handler\\n    if patchCheckSumDict[\\\"status\\\"] == \\\"pending\\\":\\n\"]}"
  },
  {
    "Input": {
      "PatchInstallOn": "DEV-JUN_20_2021_14_0_5HRS",
      "Patch_Phase": "pre-patch",
      "S3_Bucket": "dxc",
      "S3_directory_name": "JUN_2021/ap-south-1/patchJobId_98d80322-c0a9-11eb-b95e-5f544c2b0dea"
    },
    "Execution": "arn:aws:states:ap-south-1:338395754338:execution:PatchingE2EAutomationPatchScanReport:02f5b024-961d-36bb-8ca5-68dd16723973",
    "StateMachine": {
      "Id": "arn:aws:states:ap-south-1:338395754338:stateMachine:PatchingE2EAutomationPatchScanReport",
      "Name": "PatchingE2EAutomationPatchScanReport"
    }
  }
]

if __name__ == "__main__":
      lambda_handler(event1, "")

'''
    event1 = [
  {
    "Status": "completed",
    "Count": 9,
    "PatchInstallOn": "DEV-JUN_20_2021_14_0_5HRS",
    "S3_Bucket": "dxc",
    "S3_directory_name": "JUN_2021/ap-south-1/patchJobId_98d80322-c0a9-11eb-b95e-5f544c2b0dea",
    "Phase": "post"
  },
  {
    "S3_Bucket": "dxc",
    "Phase": "post",
    "S3_directory_name": "JUN_2021/ap-south-1/patchJobId_98d80322-c0a9-11eb-b95e-5f544c2b0dea",
    "PatchInstallOn": "DEV-JUN_20_2021_14_0_5HRS"
  }
]


event2 = [
  {
    "Cause": "{\"errorMessage\": \"'NoneType' object is not subscriptable\", \"errorType\": \"TypeError\", \"stackTrace\": [\"  File \\\"/var/task/lambda_function.py\\\", line 35, in lambda_handler\\n    TagValues = event[\\\"PatchInstallOn\\\"]\\n\"]}"
  },
  {
    "S3_Bucket": "dxc",
    "S3_directory_name": "JUN_2021/ap-south-1/patchJobId_98d80322-c0a9-11eb-b95e-5f544c2b0dea",
    "PatchInstallOn": "DEV-JUN_20_2021_14_0_5HRS"
  }
]

[
  {
    "Execution":"arn:aws:states:ap-south-1:338395754338:execution:AWSPatchScanReportStateMachine-QE5XoB5L7ad7:8bdd96a2-3d9d-967a-406a-e968298b180c",
    "Cause": "{\"errorMessage\": \"'NoneType' object is not subscriptable\", \"errorType\": \"TypeError\", \"stackTrace\": [\"  File \\\"/var/task/lambda_function.py\\\", line 35, in lambda_handler\\n    TagValues = event[\\\"PatchInstallOn\\\"]\\n\"]}"
  },
  {
    "S3_Bucket": "dxc",
    "S3_directory_name": "JUN_2021/ap-south-1/patchJobId_98d80322-c0a9-11eb-b95e-5f544c2b0dea",
    "PatchInstallOn": "DEV-JUN_20_2021_14_0_5HRS"
  }
]

event3 = [
  {
    "Status": "completed",
    "Count": 9,
    "PatchInstallOn": "DEV-JUN_20_2021_14_0_5HRS",
    "S3_Bucket": "dxc",
    "S3_directory_name": "JUN_2021/ap-south-1/patchJobId_98d80322-c0a9-11eb-b95e-5f544c2b0dea",
    "Phase": "post"
  },
  {
    "S3_Bucket": "dxc",
    "Phase": "post",
    "S3_directory_name": "JUN_2021/ap-south-1/patchJobId_98d80322-c0a9-11eb-b95e-5f544c2b0dea",
    "PatchInstallOn": "DEV-JUN_20_2021_14_0_5HRS"
  }
]
'''