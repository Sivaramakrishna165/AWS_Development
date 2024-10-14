'''
[AWSPE-6823]
This is a lambda function, which backup the rules and configuration of the existing webacl and
export that configuration into S3 bucket.
This Lambda function will be invoked by the cron expression once in a day at 10 AM, and also we are creating
Lifecycle management rule for the S3 bucket objects which will delete the bucket objects after 30 days .
'''
import boto3
import json
import os
from boto_helper import BotoHelper

# Create an instance of BotoHelper
boto_helper = BotoHelper()

# Create an WAFV2 and S3 client
wafv2_client = boto3.client('wafv2')
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    try:
        # Get the webacl parameter from environment variables
        original_webacl_arn = os.environ.get('WafWebAclArn')
        print("ORIGINAL_WEBACL_ARN ====> ", original_webacl_arn)
        
        # retrieve bucket name from environment variable to store the waf rules and configurations 
        bucket_name = os.environ.get('S3BucketNameForWafBackup')

        # Extract WebACL configuration details

        # Retrieve webacl name from webACL ARN
        split_arn_to_get_webacl_name = original_webacl_arn.split(':')[-1]
        original_webacl_name = split_arn_to_get_webacl_name.split('/')[2]

        # Retrieve webacl Scope from webacl ARN
        split_arn_to_get_webacl_scope = original_webacl_arn.split(':')
        original_webacl_scope = split_arn_to_get_webacl_scope[5].upper().split('/')[0]  # REGIONAL

        # Retrieve webacl Region from webacl ARN
        original_webacl_region_name = original_webacl_arn.split(':')[3]

        # Retrieve webacl Id from webacl ARN
        split_arn_to_get_webacl_id = original_webacl_arn.split(':')[-1]
        original_webacl_id = split_arn_to_get_webacl_id.split('/')[3]

        get_existing_webacl_config = get_existing_webacl_dr(original_webacl_name, original_webacl_scope, original_webacl_id)

        print("WEBACL_RESPONSE ====>", get_existing_webacl_config)

        # bucket creation for storing backup of the WAF Rules and Configurations
        creating_bucket_to_store_backup(bucket_name, original_webacl_region_name)

        # Backup the rules and configuration regarding WAF
        backup_data = {
            'WebACL': get_existing_webacl_config
        }

        # uploading a backup of the WAF Rules to S3 bucket created above
        upload_waf_rules_backup_to_S3_bucket(bucket_name, backup_data)

        # creating a lifecycle management rule for S3 bucket
        lifecycle_rule_for_deleting_objects_in_S3_bucket(bucket_name)

    except Exception as e:
        print(f'Error: {str(e)}')

def get_existing_webacl_dr(original_webacl_name, original_webacl_scope, original_webacl_id):
    get_existing_webacl_dr_response = boto_helper.get_existing_webacl(wafv2_client, original_webacl_name, original_webacl_scope, original_webacl_id)
    return get_existing_webacl_dr_response

def creating_bucket_to_store_backup(bucket_name, original_webacl_region_name):
    create_bucket_and_store_backup = boto_helper.create_bucket(s3_client, bucket_name, original_webacl_region_name)
    return create_bucket_and_store_backup

def upload_waf_rules_backup_to_S3_bucket(bucket_name, backup_data):
    upload_backup_to_s3_bucket = boto_helper.upload_waf_rules_as_backup(s3_client, bucket_name, backup_data)
    return upload_backup_to_s3_bucket

def lifecycle_rule_for_deleting_objects_in_S3_bucket(bucket_name):
    lifecycle_rules_for_S3 = boto_helper.bucket_object_lifecycle_expiration(s3_client, bucket_name)
    return lifecycle_rules_for_S3
