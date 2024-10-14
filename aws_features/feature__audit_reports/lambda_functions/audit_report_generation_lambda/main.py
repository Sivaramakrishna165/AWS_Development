import boto3
from dateutil.tz import tzutc
import json 
import os

from botocore.config import Config

"""
Feature that can run a report on a scheduled basis, and send the results to a ServiceNow incident,
As MVP, generated report will be dropped in a s3 bucket and location details will be shared in the incident

The first item : listing of IAM users, and when the access was last used.

By : Sathyajith Puttaiah
"""

from iam_users_audit_report import iam_users_audit_report
iam_users_audit_report_obj = iam_users_audit_report()

config=Config(retries=dict(max_attempts=10,mode='standard'))
ssm_client = boto3.client('ssm', config=config)

def lambda_handler(event, context):

    print('received event:',event)
    print('received context:',vars(context))

    account_id = context.invoked_function_arn.split(':')[4]

    try:
        resource_param = os.environ['RESOURCES_DET_PARAM']
        snow_topic = os.environ['SNOW_TOPIC']
        snow_desc_param = os.environ['SNOW_DESC_PARAM']

        audits_tobe_done = ssm_client.get_parameter(Name = resource_param,
                                            WithDecryption=True)['Parameter']['Value']
        audits_tobe_done = audits_tobe_done.split(",")
        print('audits_tobe_done:',audits_tobe_done)

        for rsce in audits_tobe_done:
            if rsce == 'IAM_USERS':
                iam_users_audit_report_obj.processor(account_id,snow_topic,snow_desc_param)
                print('process for IAM_USERS audit report has been comepleted')
    
    except Exception as e:
        print('error in lambda_handler():',e)
        raise

    
