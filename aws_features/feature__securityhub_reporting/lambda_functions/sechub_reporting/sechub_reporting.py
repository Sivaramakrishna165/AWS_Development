import boto3
from dateutil.tz import tzutc
import json 
import os

from botocore.config import Config

"""
Feature that can generate Security Hub export to s3 when ever a new finding generates or existing finding
get updated.

By : Sathyajith Puttaiah
"""

from helper import sechub_export
sechub_export_helper_obj = sechub_export()

def lambda_handler(event, context):
    print('received event:',event)
    print('received context:',vars(context))
    record_count = 0
    
    try:
        account = context.invoked_function_arn.split(':')[4]
        for record in event['Records']:
            if('awsRegion' in record):
                region = record['awsRegion']
            else:
                region = context.invoked_function_arn.split(':')[3]
            bucket = record['s3']['bucket']['name']
            object_key = record['s3']['object']['key']
            partition = '/'.join(object_key.split('/')[2:-2])
            object_name = object_key.split('/')[-1]
            
            findings_list = sechub_export_helper_obj.get_findings(bucket,object_key)
            record_count += len(findings_list)
            output = sechub_export_helper_obj.process_findings(findings_list, region, account)
            sechub_export_helper_obj.create_s3_object(output,bucket,partition,object_name)
            
        print('Processed {a} number of logs'. format(a=record_count))
        print('-------------------Process Completed-------------------')
        
    except Exception as e:
        print('error in handler():',e)