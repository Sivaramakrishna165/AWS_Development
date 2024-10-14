'''
boto_helper class contains all the methods related to boto3 operations
'''
import boto3
import json
import time
import urllib.parse
import http.client
import boto3.session
import botocore
from botocore.config import Config

class BotoHelper():
    def __init__(self):
        self.config = Config(retries=dict(max_attempts=10, mode='standard'))
        self.tags = [{'Key': 'Owner', 'Value': 'DXC'}, {'Key': 'Application', 'Value': 'AWS Managed Services'}]
        self.ses_client = boto3.client('ses', config=self.config)
        self.sts_client = boto3.client('sts', config=self.config)
        self.s3_client = boto3.client('s3', config=self.config)
        self.s3_resource = boto3.resource('s3', config=self.config)

    
    def check_sender_and_recipient_email_address_are_verified_or_not(self, sender_email_address, recipient_email_address):
        try:
            email_verified_or_not_response = self.ses_client.get_identity_verification_attributes(
                Identities=[
                    sender_email_address, 
                    recipient_email_address
                ]
            )
            return email_verified_or_not_response
        except Exception as e:
            print(f"Error: Email address identities are not verified: {e}")
            raise 

    def target_account_session(self, new_access_key_id, new_secret_access_key, new_session_token):
        try:
            target_account_session_response = boto3.session.Session(
                aws_access_key_id=new_access_key_id,
                aws_secret_access_key=new_secret_access_key,
                aws_session_token=new_session_token
            )
            return target_account_session_response
        except Exception as e:
            print(f"Error: Session is not created: {e}")
            raise

    def assume_target_account_role(self, target_account_role_arn):
        try:
            target_account_role_response = self.sts_client.assume_role(
                RoleArn=target_account_role_arn,
                RoleSessionName="sustainability_reader_session"
            )
            return target_account_role_response
        except Exception as e:
            print(f"Error: target account assume role: {e}")
            raise 

    def create_bucket(self, bucket_name, region_name):
        try:
            creation_of_s3_bucket = self.s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': region_name
                })
            print(f"Bucket - '{bucket_name}' created successfully.")
            return creation_of_s3_bucket
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
                print(f"Bucket '{bucket_name}' already exists, need not to create new bucket.")
            else:
                raise e
        except Exception as e:
            print(f'Error: {str(e)}')
    
    def save_json_to_file_in_s3_bucket(self, bucket_name, s3_obj_name, emissions_data):
        try:
            save_json_to_file_in_s3_bucket_response = self.s3_resource.Object(bucket_name, s3_obj_name).put(Body=json.dumps(emissions_data))
            return save_json_to_file_in_s3_bucket_response
        except Exception as e:
            print(f"Error saving JSON data to file inside S3 bucket: {e}")
            raise 
    
    def retrieving_object_from_s3(self, bucket_name, object_key):
        try:
            retrieving_s3_object_response = self.s3_client.get_object(Bucket=bucket_name, Key=object_key)
            return retrieving_s3_object_response
        except Exception as e:
            print(f"Error retrieving object from S3 bucket: {e}")
            raise

    def sending_json_report_over_email(self, sender_email_address, recipient_email_address, raw_message):
        try:
            sending_cf_report_as_email_response = self.ses_client.send_raw_email(
                Source=sender_email_address,
                Destinations=[recipient_email_address],
                RawMessage={'Data': raw_message}
            )
            print(f"Carbon Footprint report email is sent successfully to - {recipient_email_address}")
            return sending_cf_report_as_email_response
        except Exception as e:
            print(f"Error sending email: {e}")
            raise