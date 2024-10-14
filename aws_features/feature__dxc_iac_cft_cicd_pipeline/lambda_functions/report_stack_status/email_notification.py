'''
Email 
'''
import boto3
import os,sys
import json
from json2html import *
from botocore.config import Config

class email_notification():
    def __init__(self, sender, recipient):
        
        self.config=Config(retries=dict(max_attempts=10,mode='standard'))
        self.ses_client = boto3.client('ses', config=self.config)
        
        self.sender = sender
        self.recipient = recipient.split(',')
            
    def send_email(self, stacks_lst, pipeline, account='', deploy_acc='', region='', deploy_region=''):
        try:
            SUBJECT = 'DXC AWSMS CICD Pipeline - CFTs deployment report'
        
            html_data = json2html.convert(json = stacks_lst, table_attributes="style=\"border: 1px solid black;width: 90%;text-align: center;\"")
        
            status=''
            
            BODY_HTML = """<html>
                        <head>
                        <style>
                        table{
                            width:97%;
                            height:50%;
                            display:table;
                        }
                        th{
                            background-color: #1674b8;
                            border-bottom: 1px solid #ddd;
                            color:#ffffff;
                        }
                            table, th, td {
                            border: 1px solid black;
                            padding: 2px 2px;
                            font: 13px Verdana;
                        }
                
                        th {
                            font-weight: bold;
                        }
                        </style>
                        </head>
                        <body>
                        
                        <p>Hi, <br/><br/>
                        DXC AWSMS CICD Pipeline CFTs create/update status report.</p>
                        <p>
                        Pipeline account: <b>"""+account+"""</b> </br>
                        Pipeline region: <b>"""+region+"""</b></br>
                        Pipeline: <b>"""+pipeline+"""</b><br/><br/>
                        Templates deploy account: <b>"""+deploy_acc+"""</b></br>
                        Templates deploy region: <b>"""+deploy_region+"""</b></br>
                        </p>
                        """+html_data+"""
                        <br/><br/>
                        <p>Thanks,<br/> DXC AWSMS</p>
                        </body>
                        </html>
                        """ 
            
        except Exception as e:
            print(str(e))
            raise e
            
        # The email body for recipients with non-HTML email clients.
        BODY_TEXT = ("Amazon SES Test (Python)\r\n"
                     "This email was sent with Amazon SES using the "
                     "AWS SDK for Python (Boto)."
                    )
                    
    
        # The character encoding for the email.
        CHARSET = "UTF-8"
        
        # Try to send the email.
        try:
            #Provide the contents of the email.
            response = self.ses_client.send_email(
                Destination={
                    'ToAddresses': self.recipient,
                },
                Message={
                    'Body': {
                        'Html': {
                            'Charset': CHARSET,
                            'Data': BODY_HTML,
                        },
                        'Text': {
                            'Charset': CHARSET,
                            'Data': BODY_TEXT,
                        },
                    },
                    'Subject': {
                        'Charset': CHARSET,
                        'Data': SUBJECT,
                    },
                },
                Source=self.sender
                )
        except Exception as e:
            print('Send_Email',e)
            