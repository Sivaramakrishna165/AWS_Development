'''
This lambda script will trigger post patch step function to perform post patching activity
'''

import boto3
import os
import json
from datetime import datetime
import uuid
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

sfn_client = boto3.client("stepfunctions",config=config)

sfn_arn = os.environ['SfnArn']
#sfn_arn = 'arn:aws:states:ap-south-1:338395754338:stateMachine:PatchingE2EAutomationPerformPostTasks'

def lambda_handler(event, context):
    region = event['region']
    # now = datetime.now()
    # current_time = now.strftime("%d%m%Y%H%M%S")
    execution_id = str(uuid.uuid1())
    sfn_name = "sfn_" + str(execution_id)  
    print(sfn_name)
    event['Phase'] = 'post'
    tagValue = event['PatchInstallOn']
    tagValue = tagValue.replace("_BY_AY","")
    
    #tagValue = tagValue.split("_")
    #tagValue = tagValue[0] + "_" + tagValue[1] + "_" + tagValue[2] + "_" + tagValue[3] + "_" + tagValue[4] + "_" + tagValue[5]
    print("Tag Value is : ", tagValue)
        
    event['PatchInstallOn'] = tagValue
    
    response = sfn_client.start_execution(
        stateMachineArn = sfn_arn,
        name = sfn_name,
        input = json.dumps(event)
    )
    return event


if __name__ == "__main__":
    event1 = {"PatchInstallOn":"JUN_20_2021_14_0_4HRS","S3_Bucket": "dxc","S3_directory_name": "JUN_2021","Phase":"pre","SubSFName":"e67r54","region":"ap-south-1"}   
    lambda_handler(event1, "")
