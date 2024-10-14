from urllib import response
import pytest
import sys
import boto3
sys.path.append('../lambda_functions/audit_report_generation_lambda')
from helper import helper
import json

from moto import mock_dynamodb,mock_s3,mock_sns

@mock_dynamodb
def test_get_db_item():
    feature_name='AuditReports'
    val_to_fetch = 'pfSnowInciPriority'

    client = boto3.client("dynamodb", 
        region_name="us-east-1")

    client.create_table(
        TableName="TEST-Table",
        KeySchema=[
            {"AttributeName": "Feature", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "Feature", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 5},
    )

    print('create_table done')
    client.put_item(
        TableName='TEST-Table',
        Item={
            "Feature": {"S": "AuditReports"},
            "Email": {"S": "Check this out!"},
            "FeatureParams": {
                            "M": {
                            "pfAuditReportGenCron": {
                                "M": {
                                "Default": {
                                "S": "cron(15 3 * * ? *)"
                                },
                                "Description": {
                                "S": "Cron exprssion to schedule, creates the audit report for all the mentioned resources"
                                },
                                "Type": {
                                "S": "String"
                                }
                                }
                            },
                            "pfAWSResources": {
                                "M": {
                                "Default": {
                                "S": "IAM_USERS"
                                },
                                "Description": {
                                "S": "Resources for which report needs to be generated. Ex - IAM_USERS Values must be comma separated and from the list given below Allowed Values - IAM_USERS"
                                },
                                "Type": {
                                "S": "String"
                                }
                                }
                            },
                            "pfShortDescForSNOW": {
                                "M": {
                                "Default": {
                                "S": "Audit Reports for IAM Users"
                                },
                                "Description": {
                                "S": "Short Description which will be used while creating the SNOW incident."
                                },
                                "Type": {
                                "S": "String"
                                }
                                }
                            },
                            "pfSnowInciPriority": {
                                "M": {
                                "AllowedValues": {
                                "L": [
                                {
                                    "S": "1"
                                },
                                {
                                    "S": "2"
                                },
                                {
                                    "S": "3"
                                },
                                {
                                    "S": "4"
                                },
                                {
                                    "S": "5"
                                }
                                ]
                                },
                                "Default": {
                                "S": "4"
                                },
                                "Description": {
                                "S": "Priority of the incident to be created for Audit notification"
                                },
                                "Type": {
                                "S": "String"
                                }
                                }
                            }
                            }
                            }
        },
    )
    print('put item completed')

    boto_obj = helper()
    response = boto_obj.get_db_object('TEST-Table',feature_name,val_to_fetch)
    print(response)

@mock_s3
def test_s3_upload_object():

    key_name = 'testkey.json'
    folder = 'test_folder'
    filename = 'testfile.csv'
    final_report = [{'Test':'Mock'}]
    bucket = 'bucket'
    boto_obj = helper()

    s3 = boto3.client("s3", region_name='us-east-1')
    s3.create_bucket(Bucket=bucket)

    boto_obj.create_s3_file(bucket,final_report,folder,filename)

@mock_sns
def test_sns():
    message="test message"

    conn  = boto3.client("sns", region_name='us-east-1')
    conn.create_topic(Name="some-topic")
    response = conn.list_topics()
    topic_arn = response["Topics"][0]["TopicArn"]

    conn.subscribe(
        TopicArn=topic_arn,
        Protocol="email",
        Endpoint="user@example.com",
    )

    boto_obj.send_to_snow(message,topic_arn)


if __name__ == "__main__":
     test_get_db_item()
     test_s3_upload_object()
     test_sns()