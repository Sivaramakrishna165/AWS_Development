'''
Boto Helper class contain all the supported aws api operations
'''
import json
import os
import boto3
import urllib.parse
import http.client
from botocore.config import Config

class boto_helper():
    
    def __init__(self):
        self.config = Config(retries=dict(max_attempts=10,mode='standard'))
        self.s3_client = boto3.client('s3', config=self.config)
        
    #To fetch the list of s3 buckets
    def fetch_s3_bucket(self):
        try:
            s3_response=self.s3_client.list_buckets()
            bucketlist=s3_response['Buckets']
            return bucketlist
        except Exception as e:
            print('error', e)
            return
        
    #To fech the S3 buckets contains specific tag key
    def fetch_s3_bucket_with_tag(self,bucketname):
        try:
            s3_tags_response=self.s3_client.get_bucket_tagging(
                Bucket=bucketname
            )
            return s3_tags_response
        except Exception as e:
            pass
    
    #To fetch the versioning status of the s3 bucket
    def get_s3_bucket_versioning_status(self,bucket):
        try:
            versioning_status_response=self.s3_client.get_bucket_versioning(
            Bucket=bucket
            )
            return versioning_status_response
        except Exception as e:
            print('error', e)
            return
    
    #To enable versioning on the s3 bucket
    def s3_enable_versioning(self,bucket):
        try:
            versioning_response = self.s3_client.put_bucket_versioning(
                Bucket=bucket,
                VersioningConfiguration={
                    'Status': 'Enabled'
                }
            )
        except Exception as e:
            print('error', e)
            
    #To send the response back to cfn template
    def send_response(self,request, response, status=None, reason=None):
        if status is not None:
            response['Status'] = status
        if reason is not None:
            response['Reason'] = reason
        if 'ResponseURL' in request and request['ResponseURL']:
            try:
                url = urllib.parse.urlparse(request['ResponseURL'])
                body = json.dumps(response)
                https = http.client.HTTPSConnection(url.hostname)
                https.request('PUT', url.path + '?' + url.query, body)
                print('Response sent successfully')
            except:
                print("Failed to send the response to the provided URL")
        return response        