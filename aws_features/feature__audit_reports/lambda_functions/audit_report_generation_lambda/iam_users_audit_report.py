import boto3
import datetime
from dateutil.tz import tzutc
import json 
import os
import time

from botocore.config import Config
from helper import helper
helper_obj = helper()

class iam_users_audit_report():

    def __init__(self):

        self.currentDT = datetime.datetime.now()
        self.Date = self.currentDT.strftime("%Y%m%d")
        self.Date_time= self.currentDT.strftime("%Y%m%d_%H%M%S")

        config=Config(retries=dict(max_attempts=10,mode='standard'))
        self.iam_client=boto3.client('iam',config=config)
        self.iam_resource = boto3.resource('iam',config=config)
        self.ddb = boto3.resource('dynamodb', config=config)
        self.ssm_client = boto3.client('ssm', config=config)

        self.folder = 'iam-users/'+self.Date
        self.filename = 'IAM_User_Details_'+ self.Date_time +'.csv'

        self.bucket_name = os.environ['AUDIT_BUCKET']
        self.table_name = 'AccountFeatureDefinitions'
        self.feature_name = 'AuditReports'
        self.val_to_fetch = 'pfSnowInciPriority'

        self.table = self.ddb.Table(self.table_name)
    
    def iam_audit_report(self,account_id,snow_topic,snow_desc_param):
        try:

            #paginator for iam users
            paginator=self.iam_client.get_paginator('list_users')

            count=1
            final_report = 'Sl NO|User Name|Last Accessed On|Days Back\n'
            
            #looping all the pages
            for pages in paginator.paginate():
                #looping the users
                for users in pages['Users']:
            
                    last_access = None
                    
                    user = self.iam_resource.User(users['UserName'])
                    
                    #there might be multiple access keys for an user.loop thru all those and fetch the latest user date
                    for k in user.access_keys.all():
                        key_used = self.iam_client.get_access_key_last_used(AccessKeyId=k.id) 

                        if 'LastUsedDate' in key_used['AccessKeyLastUsed']:
                            accesskey_last_used = key_used['AccessKeyLastUsed']['LastUsedDate']
                            
                            if last_access is None or accesskey_last_used < last_access:
                                last_access = accesskey_last_used
                    
                    #checking if the user had logged in using the password and taking the latest b/w access key and password
                    if last_access is not None:
                        if user.password_last_used is not None and user.password_last_used > last_access:
                            last_access = user.password_last_used
                        
                        delta = (self.currentDT - last_access.replace(tzinfo=None)).days
                        
                    else:
                        delta = 'NULL'
                        
                    if last_access is None:
                        last_access = 'NULL'
                    
                    #fetch all the user details into final_report
                    #final_report += str(count) + "|username: " + users['UserName'] + "|last accessed on:" + str(last_access) + "|"+ str(delta) +" days back\n"
                    final_report += str(count) + "|" + users['UserName'] + "|" + str(last_access) + "|"+ str(delta) +"\n"

                    count +=1
                    
            print('total users => ',count-1)
            #print('final_report:',final_report)
            
            #create a file in s3
            helper_obj.create_s3_file(self.bucket_name,final_report,self.folder,self.filename)

            message = self.prepare_payload(self.bucket_name,self.folder,self.filename,account_id,snow_desc_param)

            helper_obj.send_to_snow(message,snow_topic)
        
        except Exception as e:
            print('error in iam_audit_report():',e)
            raise
    
    def prepare_payload(self,Bucket,Folder,File_Name,account_id,snow_desc_param):
        try:

            priority_val = helper_obj.get_db_object(self.table,self.feature_name,self.val_to_fetch)

            snow_desc =  self.ssm_client.get_parameter(Name = snow_desc_param,
                                            WithDecryption=True)['Parameter']['Value']

            eventsourcesendingserver = 'Audit Reporting'
            region = os.environ['AWS_REGION']

            long_desc = """Audit Report for IAM Users has been created. Please find the file in below mentioned location
Bucket : %s 
Folder : %s 
File_Name : %s 
Region : %s
Account : %s """ % (Bucket,Folder,File_Name,region,account_id)

            message = {
                        "EventList":[
                        {
                            "eventsourcesendingserver": eventsourcesendingserver,
                            "eventsourceexternalid": self.Date_time,
                            "title": snow_desc,
                            "longDescription": long_desc,
                            "application": eventsourcesendingserver,
                            "eventsourcecreatedtime": self.Date_time,
                            "PriorityData": {
                                "Priority": priority_val
                            }
                        }    
                        ] 
                    }
            return message
        
        except Exception as e:
            print('error in prepare_payload():',e)

    
    def processor(self,account_id,snow_topic,snow_desc_param):
        self.iam_audit_report(account_id,snow_topic,snow_desc_param)
