"""
It is sending the  war workloads data to users
"""
import boto3
from botocore.config import Config
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from botocore.exceptions import ClientError
from datetime import date

config=Config(retries=dict(max_attempts=10,mode='standard'))

ses_client = boto3.client('ses',config=config)

# Monitor_ARN = os.environ['MonitorARN']
cloudOpsEmailId = os.environ['cloudOpsEmailId']
SenderEmailId = os.environ['SenderEmailId']

def read_ssm_parameter(name):
    ssm_para_client = boto3.client('ssm',config=config)
    response = ssm_para_client.get_parameter(
        Name=name,
    )
    ssm_parameter = response['Parameter']
    ssm_parameter_value = ssm_parameter['Value']
    return ssm_parameter_value

def send_mail(SENDER,recipientMailIDs,msg):
    try:
        # print("send_mail triggered.")
        # recipientMailIDs = ['s.sanika@dxc.com']
        if len(recipientMailIDs) != 0:
            print("Trying to send mail to : ",recipientMailIDs)
            try:
                response = ses_client.send_raw_email(
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
                print("Error in sendmail : ",e)
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
        print("email sent.")
    except Exception as e:
        print("Error send_mail() - ",e)

def create_html_body(account_id,AccountName,Regions,Workloads,HighRisks,owners_mails,year,month):
    try:
        print("html_body triggered.")
        SENDER = read_ssm_parameter(SenderEmailId)
        # sender = 's.sanika@dxc.com'
        print("Sender's email_is : ", SENDER)
        CloudOpsTeamEmail_ids = read_ssm_parameter(cloudOpsEmailId)
        print("CloudOpsTeamEmail_ids : ",CloudOpsTeamEmail_ids)
        AccountName = boto3.client('iam',config=config).list_account_aliases()['AccountAliases'][0]
        # account_id = boto3.client("sts").get_caller_identity()["Account"]
        # recipient_mails = ['s.sanika@dxc.com']
        value = CloudOpsTeamEmail_ids
        recipientMailIDs = []
        rejected_mails = []
        for toMailId in value.split(";"):
            if toMailId != "":
                recipientMailIDs.append(toMailId)
        for mail in owners_mails:
            if mail != "":
                recipientMailIDs.append(mail)
        # recipientMailIDs=['s.sanika@dxc.com']
        print("\nTo Mail ID : ", recipientMailIDs)
        response = ses_client.get_identity_verification_attributes(
            Identities=recipientMailIDs
        )
        for i in recipientMailIDs:
            if i in response['VerificationAttributes'].keys():
                if response['VerificationAttributes'][i]['VerificationStatus'] == 'Success':
                    continue
            rejected_mails.append(i)
                    
        print("emails not verified: " + str(rejected_mails))

        recipient_mails = list(set(recipientMailIDs) - set(rejected_mails))
        print("verified emails: " + str(recipient_mails))
        CHARSET = "utf-8"
        SUBJECT = f"AWS Monthly WAR Reporting Dashboard for {month} {year} - {account_id}"
        message = MIMEMultipart("mixed")
        message['Subject'] = SUBJECT 
        message['From'] = SENDER
        message['To'] = ','.join(recipient_mails)

        table = "<table>"
        table = table + "<tr><td>Account ID </td><td>" + str(account_id) + "</td></tr>"
        table = table + "<tr><td>Account Name </td><td>" + str(AccountName) + "</td></tr>"
        table = table + "<tr><td>Regions </td>" 
        for region in Regions:
            table = table + "<td>"+str(region) + "</td>"
        table = table + "</tr>"
        table = table + "<tr><td>Workloads </td>"
        for workload in Workloads:
            table = table + "<td>"+str(workload) + "</td>"
        table = table + "</tr>"
        # table = table + "<tr><td>HighRisks </td><td>" + str(HighRisks) + "</td></tr>"
        table = table + "<tr><td>HighRisks </td>"
        for highrisk in HighRisks:
            table = table + "<td>"+str(highrisk) + "</td>"
        table = table + "</tr>"
        table = table + "</table>"

        html = """ <html>
                <head>
                <style> 
                table, th, td {{ border: 2px solid black; }}
                th, td {{ border: 1.5px solid black; background-color: #f0f0f0; }}
                </style>
                </head>
                <body>
                <p style = "font-weight: bold;font-size: 20px;">AWS Well Architected Review - Reporting Summary for {month} {year}</style></p>
                <p>Hello Team,</p>
                <p>Greetings !</p>
                <p>Please find the below table for WAR Workloads summary!!</p>
                <p>     """
        html = html + table
        html = html + """  <p>Kindly refer the below link to access Centralized PowerBI Dashboard for more details: </p>
                            <p>https://app.powerbi.com/reportEmbed?reportId=d01288f4-9a7f-44a7-9f94-b8d50aba450b&appId=33a60d5a-0c3b-4a2e-81de-b1f2759e25fd&autoAuth=true&ctid=93f33571-550f-43cf-b09f-cd331338d086.</p>
                            </p><br>
                           <p>Regards,</p>
                           <p>Cloud Automation Team</p>
                           </body>
                           </html> """ 
        html = html.format(month = month,year = year,table = table)
        try:
            msg_body = MIMEMultipart('alternative')
            # textpart = MIMEText(BODY_TEXT.encode(CHARSET), 'plain', CHARSET)
            htmlpart = MIMEText(html.encode(CHARSET), 'html', CHARSET)                
            # msg_body.attach(textpart)
            msg_body.attach(htmlpart)
            message.attach(msg_body) 
            #print(type(message))
            # send_mail(html,account_id,tagvalue)         
            send_mail(SENDER,recipient_mails,message)
        except Exception as e:
            print("error in in msg body : ",e)
    except Exception as e:
        error_status = True 
        html=''
        print("Error html_body() - ",e)

def lambda_handler(event, context):
    try:
        print('Received event is ',event)
        AccountName = boto3.client('iam',config=config).list_account_aliases()['AccountAliases'][0]
        account_id = boto3.client("sts").get_caller_identity()["Account"]
        Regions = event['Regions']
        Workloads = event['Workloads']
        HighRisks = event['HighRisks']
        owners = event['owners']
        owners_mails = list(dict.fromkeys(owners))
        todays_date = date.today()
        year = todays_date.year
        
        print("Current year:", year) 

        months = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}
        month = months[todays_date.month]
        print("Current month:",month)
        create_html_body(account_id,AccountName,Regions,Workloads,HighRisks,owners_mails,year,month)
         
    except Exception as e:
        print("Error in lambda_handler ",e)
       