'''
NOTE: Lambda function name will be dynamically allocated while stack creation
=========
Purpose
=========
This lambda function is a DeployStage action of the CICD Pipeline.On successful execution of the pipeline, this lambda is triggered.

=============
Functionlaity
=============
Retrives all the CFTs and Configuration CFTs from S3 bucket and invokes rCicdExecCftsLambda function for CREATE/DEPLOY stacks

Created By: Kedarnath Potnuru
Date: 14 Apr 2023

'''
import json
import boto3
import os
from botocore.config import Config
config = Config(retries=dict(max_attempts=10,mode='standard'), signature_version='s3v4')
create_update_stack_lambda = os.environ['CreateCFTLambda']

def lambda_handler(event, context):
    print('Event received',event)
    s3_resource = boto3.resource('s3', config=config)
    lambda_client = boto3.client('lambda', config=config)
    cp_client = boto3.client('codepipeline', config=config)
    
    data = event['CodePipeline.job']['data']
    
    input_params = data['actionConfiguration']['configuration']['UserParameters']
    if(isinstance(input_params, str)):
        input_params = json.loads(input_params)
    
    artifacts_bucket = input_params['Bucket']
    artifacts_folder_key = input_params['Key'] + "/"
    pipeline = input_params['StackName']
    
    templates_list = []
    bucket = s3_resource.Bucket(artifacts_bucket)
    
    for object_summary in bucket.objects.filter(Prefix=artifacts_folder_key):
        templates_list.append(object_summary.key)
    
    filter_templates = [obj for obj in templates_list if 'configuration' not in obj]
    
    for obj in filter_templates:
        template = obj.split('.')[0]
        temp_config = template+ '-configuration.json'
        
        lambda_payload = {}
        lambda_payload['Template'] = obj
        lambda_payload['Bucket'] = artifacts_bucket
        lambda_payload['Pipeline'] = pipeline
        lambda_payload['Configuration'] = temp_config if temp_config in templates_list else ''
        
        lambda_client.invoke(
            FunctionName=create_update_stack_lambda.split(':')[-1],
            InvocationType='Event',
            Payload=json.dumps(lambda_payload))
        
        print('Payload sent success', lambda_payload)
    
    cp_client.put_job_success_result(
        jobId = event['CodePipeline.job']['id']
    )
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
