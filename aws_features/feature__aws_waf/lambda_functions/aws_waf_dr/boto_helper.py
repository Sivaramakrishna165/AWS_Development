import boto3
import json
import time
import datetime
import botocore
from botocore.config import Config


class BotoHelper():
    def __init__(self):
        self.config = Config(retries=dict(max_attempts=10, mode='standard'))
        self.tags = [{'Key': 'Owner', 'Value': 'DXC'}, {'Key': 'Application', 'Value': 'AWS Managed Services'}]
        self.wafv2_client = boto3.client('wafv2', config=self.config)
        self.s3_client = boto3.client('s3', config=self.config)

    def get_existing_webacl(self, wafv2_client, webacl_name, webacl_scope, webacl_id):
        try:
            get_existing_web_acl_response = self.wafv2_client.get_web_acl(Name=webacl_name, Scope=webacl_scope, Id=webacl_id)
            return get_existing_web_acl_response
        except Exception as e:
            print("Error : ", str(e))

    def create_bucket(self, s3_client, bucket_name, original_webacl_region_name):
        try:
            creation_of_s3_bucket = s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': original_webacl_region_name
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

    def upload_waf_rules_as_backup(self, s3_client, bucket_name, backup_data):
        try:
            # Upload the backup data to S3
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            backup_file_path = f'waf_rules_backup_{timestamp}.json'
            s3_object_key = f'file/{backup_file_path}'
            backing_up_waf_rules_and_configurations = self.s3_client.put_object(Bucket=bucket_name, Key=s3_object_key, Body=json.dumps(backup_data))
            print("BACKING_UP_WAF_RULES_AND_CONFIGURATIONS ===> ", backing_up_waf_rules_and_configurations)
            print(f'=========== Backup exported and uploaded to S3: s3://{bucket_name}/{s3_object_key} ===========')
            return backing_up_waf_rules_and_configurations
        except Exception as e:
            print(f'Error: {str(e)}')

    def bucket_object_lifecycle_expiration(self, s3_client, bucket_name):
        try:
            object_expiration_from_s3_bucket = s3_client.put_bucket_lifecycle_configuration(
                Bucket=bucket_name,
                LifecycleConfiguration={
                    'Rules': [
                        {
                            'Expiration': {
                                'Days': 30
                            },
                            'Prefix': '',
                            'ID': 'Delete objects in 30 days',
                            'Status': 'Enabled'
                        }
                    ]
                }
            )
            print("=========== CREATED LIFECYCLE RULE FOR ABOVE CREATED BUCKET TO SAVE COST ===========")
            return object_expiration_from_s3_bucket
        except Exception as e:
            print(f'Error: {str(e)}')