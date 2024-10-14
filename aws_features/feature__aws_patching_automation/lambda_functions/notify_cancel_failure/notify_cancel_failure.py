'''
This lambda script is used to notify the error to user if there is an issue on cancel step function
'''

import boto3
import os
import sys
import json
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

#Prints Error with Line Number
def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    captureErr = "Line No. : " + str(lineno)  + " | ERROR: " + str(exc_obj)
    return captureErr

#Gets value of SSM parameter
def read_ssm_parameter(name):
    ssm_para_client = boto3.client('ssm',config=config)
    response = ssm_para_client.get_parameter(
        Name=name,
    )
    ssm_parameter = response['Parameter']
    parameter_value = ssm_parameter['Value']
    ssm_parameter_value = parameter_value.split(";")
    return ssm_parameter_value

#Sends and/or retries email
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


#Prepares email body
def email_body_content(State,State_Machine_Name,State_Machine_Id,Region,Account_id):
    try:
        print("Region ==> ",Region)
        print("Account_id == > ",Account_id)
        print("State ==> ", State)

        SENDER = read_ssm_parameter(SenderEmailId)
        SENDER = SENDER[0]
        print("Sender's email_is : ", SENDER)

        recipientMailIDs = read_ssm_parameter(cloudOpsEmailId)
        print("Recipient email_id : ",recipientMailIDs)
        CHARSET = "utf-8"
        SUBJECT = "ERROR AWS " + Account_id + " PE2E Automation | Patch Cancel Step Function Failed" 
        message = MIMEMultipart("mixed")
        message['Subject'] = SUBJECT 
        message['From'] = SENDER
        message['To'] = ','.join(recipientMailIDs)

        # Create the plain-text and HTML version of your message
        BODY_TEXT = """ """
        
        table = "<table>"
        table = table + "<tr><td>Account ID </td><td>" + str(Account_id) + "</td></tr>"
        table = table + "<tr><td>Region </td><td>" + str(Region) + "</td></tr>"
        table = table + "<tr><td>State Machine </td><td>" + str(State_Machine_Name) + "</td></tr>"
        table = table + "<tr><td>Execution ID </td><td>" + str(State_Machine_Id) + "</td></tr>"
        table = table + "<tr><td>Error occured at : </td><td>" + str(State) + "</td></tr>"

        BODY_HTML = """ <html>
            <head><style>table, th, td { border: 1px solid black;}</style></head>
            <body>
            <p style = "font-weight: bold;font-size: 20px;color:red;">PATCHING WINDOW CANCELLATION FAILED</style></p>
            <p>Hi Team,</p>
            <p>Cancellation of Scheduled Patching activity  FAILED. Please find the details in below.</p>
             """
        BODY_HTML = BODY_HTML + table + "</table>"
        BODY_HTML = BODY_HTML + """
                                <p> Thanks! </p>
                                <p> Regards, </p>
                                <p> CloudOps Automation 
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
    try:
        #print(event)
        Execution = event["Execution"]
        State = event["ErrorMessageFrom"]
        #State_Machine_Name = event["StateMachine"]['Name']
        #State_Machine_Id = event['StateMachine']['Id']
        Execution_content = Execution.split(":")
        State_Machine_Name = Execution_content[6]
        State_Machine_Id = Execution_content[7]
        Account_id = Execution_content[4]
        Region = Execution_content[3]
        print("Step = ",State)
        print("State_Machine_Name = ",State_Machine_Name)
        print("State_Machine_Id = ",State_Machine_Id)
        print("Account_id = ",Account_id)
        print("Region = ",Region)
        email_body_content(State,State_Machine_Name,State_Machine_Id,Region,Account_id)
        return event
    except:
        print(PrintException())
    

event1 = {'StateMachine': '$$.StateMachine', 'ErrorMessageFrom': 'CreateCloudWatchRules Function', 'Execution': 'arn:aws:states:ap-south-1:338395754338:execution:DXC_PE2EA_SFN_SchedulePatching:4504c2ba-586f-483d-56bf-7ceea24f042b', 'Cause': '{"errorMessage": "name \'patchJobId\' is not defined", "errorType": "NameError", "stackTrace": ["  File \\"/var/task/create_cloudwatchRule.py\\", line 255, in lambda_handler\\n    update_item_dynamoDB(patchJobId,\\"backup_state_status\\",\\"scheduled\\")\\n"]}'}


if __name__ == "__main__":
      lambda_handler(event1, "")
