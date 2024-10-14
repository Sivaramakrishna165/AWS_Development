'''
This Lambda script which is triggered by SNS to invoke another lambda function with specific input
'''

import boto3
import json
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))


s3_client = boto3.client("s3",config=config)
s3_resource = boto3.resource('s3')

# def create_csv_file(S3_Bucket,command_id,command_status):
#     Command_id = command_id
#     Command_Status = command_status
#     #localFolder = "/tmp/"
#     #local_folder = 'c:\\temp\\' + Command_id + '_' + Command_Status
#     local_folder = '/tmp/' + Command_id + '_' + Command_Status
#     with open(local_folder, 'w', newline = '') as csvfile:
#         pass
#     S3_Bucket = s3_resource.Bucket(S3_Bucket)
#     directory_name = 'PATCHING/' + 'status-check'
#     #local_file = "Health_Check_Validation" + '_' + TagValues + '.csv'
#     local_file = Command_id + '_' + Command_Status
#     s3Key = S3_Folder_Name + directory_name + "/" + local_file
#     S3_Bucket.upload_file(local_folder, s3Key)

def call_update_dynamodb_lambda_function(patchJob_id,attribute_name,attribute_value):
    lambda_client = boto3.client('lambda',config=config)
    dynamo_event = {'patchJob_id': patchJob_id,'attribute_name': attribute_name,'attribute_value': attribute_value}
    response = lambda_client.invoke(
        FunctionName='dxcms-pa-lam-update-dynamodb',
        Payload=json.dumps(dynamo_event)
    )


def lambda_handler(event,context):
    global S3_Folder_Name
    sns_message = json.loads(event['Records'][0]['Sns']['Message'])
    command_id = sns_message["commandId"]
    status = sns_message["status"]
    S3_Bucket = sns_message["outputS3BucketName"]
    S3_directory_name = sns_message["outputS3KeyPrefix"]
    patchJob_id = S3_directory_name.split('/')[4]
    call_update_dynamodb_lambda_function(patchJob_id,command_id,status)
    # S3_Folder_Name = S3_directory_name.split('PATCHING')[0]
    # create_csv_file(S3_Bucket,command_id,status)

# SNS Event :  {'Records': [{'EventSource': 'aws:sns', 'EventVersion': '1.0', 
# 'EventSubscriptionArn': 'arn:aws:sns:ap-south-1:338395754338:DXC_PE2EA_SNS_HealthCheckStatus:9c27d90d-1357-44a0-b130-f16a910208c3', 
# 'Sns': {'Type': 'Notification', 'MessageId': '5547b880-df9e-5ef0-b0bc-e29612250c02', 
# 'TopicArn': 'arn:aws:sns:ap-south-1:338395754338:DXC_PE2EA_SNS_HealthCheckStatus', 
# 'Subject': 'EC2 Run Command Notification ap-south-1', 
# 'Message': '{"commandId":"a7c1910e-4865-49db-a56e-07adaf32c397","documentName":"AWS-RunPowerShellScript","instanceIds":[],
# "requestedDateTime":"2021-11-23T11:07:39.457Z","expiresAfter":"2021-11-23T12:22:39.457Z",
# "outputS3BucketName":"dxc","outputS3KeyPrefix":"test/PATCHING/NOV_2021/ap-south-1/patchJobId_90963df6-46b9-11ec-b2db-8c8caa2990d1/Outputs/pre_HealthCheck/",
# "status":"Success","eventTime":"2021-11-23T11:07:39.588Z"}', 'Timestamp': '2021-11-23T11:07:39.650Z', 
# 'SignatureVersion': '1', 'Signature': 'JUd7WxlOLXPV3IF04WDZvXF86gPOKhAnYCWJ8xUC1jjBeqE/vk3yxI49Y5nVOSbIt1ovvzMHOmi5Sw1xA1EhqyjsyA+v7Q3Pa3+/+Dwuwp88HcTmsAVZUie6k5X3RFDpvss+2MrTlfH6XXina46zFbvRdUTWZhofgmu3SjjpPY03P+3e3n8sEmVudztwqVhHzGdd/rRl96hwDXf9HQjw2DWdlSGW40NyyiNdAcuswi2T+743+Gtetn3t8vPrBCJYSXPmSymU+a6dwLzIuEpR2oGCHHNxWTd7f2qGyhDA7yJUp+ewNNV4hJVdg9DBGL2rRCJ5xSVVHDt9iVwiCUHdQw==',
#  'SigningCertUrl': 'https://sns.ap-south-1.amazonaws.com/SimpleNotificationService-7ff5318490ec183fbaddaa2a969abfda.pem', 'UnsubscribeUrl': 'https://sns.ap-south-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:ap-south-1:338395754338:DXC_PE2EA_SNS_HealthCheckStatus:9c27d90d-1357-44a0-b130-f16a910208c3', 'MessageAttributes': {}}}]}

