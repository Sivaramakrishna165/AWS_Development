# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# This resembles the access to AWS Customer Carbon Footprint Tool data
# from the AWS Billing Console. Hence it is not using an official AWS interface and
# might change at any time without notice and just stop working.


'''
[AWSPE-6942]
This is a lambda function which will first retreive the carbon footprint report (.json) from the target account, and then sending that report to S3 bucket (which we are creating as part of lambda function),
by filtering the report name into the specific format and later send this report to end users as an attachment.
File formatting is important process here as sharepoint and PowerBI understands specific format (ccft_<account-id>_yymm.json) and they will do the further things expected from them only when there will be specific file format as specified.

Note - As per AWS, Carbon emissions data is available from the last 36 months. New data is available monthly, with a delay of three months.
'''

import boto3
import os
import time
import ccft_access
import json
from boto_helper import BotoHelper
from datetime import datetime, timedelta
from urllib.parse import urlencode
from botocore.exceptions import ClientError

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# Create an instance of BotoHelper
boto_helper = BotoHelper()

def lambda_handler(event, context):
    try:
        target_account_id = os.environ['TargetAccountId']
        target_account_role_name = os.environ['CcftRoleName']
        region_name = os.environ['SourceRegionName']
        bucket_name = os.environ['S3BucketName']
        sender_email_address = os.environ['SenderEmailAddress']
        recipient_email_address = os.environ['RecipientEmailAddress']

        # Sender or Receiver Email Verification
        if not sender_email_address or not recipient_email_address:
            raise ValueError("######### Sender and Recipient email addresses cannot be empty #########")
        else:
            print(f"Provided email identities - Sender Email - {sender_email_address} and Recipient Email - {recipient_email_address}")
        
        email_verification = boto_helper.check_sender_and_recipient_email_address_are_verified_or_not(sender_email_address, recipient_email_address)
        
        if sender_email_address in email_verification['VerificationAttributes'] and recipient_email_address in email_verification['VerificationAttributes']:
            if email_verification['VerificationAttributes'][sender_email_address]['VerificationStatus'] == 'Success' and email_verification['VerificationAttributes'][recipient_email_address]['VerificationStatus'] == 'Success':
                print("Both Sender and Recipient Email address identities are verified")
            else:
                raise ValueError(" ########## One or both Sender or Recipient Email address identities are not verified ########## ")
        else:
            raise ValueError("######### One or both Sender or Recipient email address is incorrect #########")
   
        # Create a new session and get credentials from target role
        target_account_role_arn = f"arn:aws:iam::{target_account_id}:role/{target_account_role_name}"
        print("TARGET_ACCOUNT_ROLE_ARN ====>", target_account_role_arn)
        
        # assuming target account role
        target_account_role = boto_helper.assume_target_account_role(target_account_role_arn)
        
        new_access_key_id = target_account_role["Credentials"]["AccessKeyId"]
        new_secret_access_key = target_account_role["Credentials"]["SecretAccessKey"]
        new_session_token = target_account_role["Credentials"]["SessionToken"]
            
        new_session = boto_helper.target_account_session(new_access_key_id, new_secret_access_key, new_session_token)
        credentials = new_session.get_credentials()
        
        try:
            statusCode = 200
            isDataAvailable = True
            
            # Get the current date
            current_date = datetime.now()
            
            # Calculate start date (As per AWS, Carbon emissions data is available from the last 36 months. New data is available monthly, with a delay of three months)
            start_date = (datetime(current_date.year, current_date.month, 1) - timedelta(days=36 * 30)).strftime('%Y-%m-%d')
            
            # Calculate end date (current month)
            end_date = datetime(current_date.year, current_date.month, 1).strftime('%Y-%m-%d')
            
            print("START_DATE ===> ", start_date) 
            print("END_DATE   ===> ", end_date) 
            
            # Format end_date as YY_MM
            formatted_end_date = end_date[2:4] + end_date[5:7]
            print("FORMATTED_END_DATE ===> ", formatted_end_date)
            
            emissions_data = ccft_access.extract_emissions_data(start_date, end_date, credentials)
            
            # creating a new S3 bucket to store account based carbon footprint reports and if the bucket is already created then save the report in already created bucket. 
            boto_helper.create_bucket(bucket_name, region_name)
            
            # save json to file in s3 bucket
            s3_obj_name = str(target_account_id)+"/"+"ccft_"+str(target_account_id)+"_"+str(formatted_end_date)+".json"
            boto_helper.save_json_to_file_in_s3_bucket(bucket_name, s3_obj_name, emissions_data)

            uploaded_cf_reports_to_s3_bucket_message = f"Successfully saved data to S3 bucket - {bucket_name} for account - {target_account_id}"
            
            print(f"Message: {uploaded_cf_reports_to_s3_bucket_message} and Data Availability: {isDataAvailable}")
            
            print("********** Waiting for 5 seconds *************")
            time.sleep(5)
            
            object_key = f'{s3_obj_name}'    
            # print("target_account_id : ", target_account_id,  "and object Key - ", object_key)
            
            get_object_from_s3 = boto_helper.retrieving_object_from_s3(bucket_name, object_key)
            json_data = get_object_from_s3['Body'].read().decode('utf-8')
            # print("JSON_DATA =====> ", json_data)
            
            attachment_data = json_data.encode('utf-8')
            subject= f'ccft_{target_account_id}_{formatted_end_date}'
            recipient_name = recipient_email_address.split("@")[0]
            # body = f'Please find the attached report containing carbon emission as per given account - {target_account_id}'
            
            body = f"""<html>
            <head>
            </head>
            <body>
              <p>Hello {recipient_name}, </p>
              <p>Attached to this email, you'll find the Carbon Footprint Report for Account - <b>{target_account_id}</b> which consists of data from <b>{start_date}</b> to <b>{end_date}</b>. </p>
              <p>Thanks, <br/> AWSPE Team </p>
            </body>
            </html>
            """ 
            attachment_filename = f'ccft_{target_account_id}_{formatted_end_date}.json'
            
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = sender_email_address  
            msg['To'] = recipient_email_address
            
            # Attach HTML Formatted body
            msg.attach(MIMEText(body, 'html'))
            
            # Attach JSON file
            attachment = MIMEApplication(attachment_data)
            attachment.add_header('Content-Disposition', 'attachment', filename=attachment_filename)
            msg.attach(attachment)
            raw_message = msg.as_string()
            
            # sending the email to recipient email address
            if json_data:
                boto_helper.sending_json_report_over_email(sender_email_address, recipient_email_address, raw_message)
                message = "Retrieved the uploaded .json carbon footprint report from S3 bucket first and then send that report to recipient email address as an attachment"
                return {
                    "statusCode" : statusCode,
                    "isDataAvailable" : isDataAvailable,
                    "emailSentToEndusers": True,
                    "message": message
                }
            else:
                print("JSON Data Unavailable : Json_date retrieval failed...")
                
        except Exception as e:
            # There are 2 things handled here in this exception: 
            # 1) If account is less than three months old, no carbon emissions data will be available 
            # 2) If the <start_date> mentioned above has month greater than 36 months, then also this exception will occur
            statusCode = 400
            isDataAvailable = False
            result = f'No carbon footprint report is available for account - {target_account_id} at this time. If no report is available, your account might be too new to show data, There is a delay of three months between the end of a month and when emissions data is available. There can be other reason for this exception if month in <start_date> is greater than 36 months'
            message = str(e)
            return {
                'statusCode': statusCode,
                'isDataAvailable': isDataAvailable,
                'message': message,
                'result': result
            }
    except Exception as e:
        print(f'Error: {str(e)}')