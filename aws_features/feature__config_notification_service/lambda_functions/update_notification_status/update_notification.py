#
# Update DynamoDB table where resources that have the
# 'Notification' attribute set to 'false'.  This
# action takes place after there has been successful
# notification sent via SNS (success result of
# SendNotification state).
#
# Trigger Type: Step Function State [UpdateNotificationStatus]
# Scope: Non-Compliant Resources in AWS Config
# Accepted Parameter: None
#

from __future__ import print_function
from boto3.dynamodb.conditions import Attr
import boto3


class GetParameterException(Exception):
    pass


class GetTableException(Exception):
    pass


class ScanTableException(Exception):
    pass


class UpdateItemException(Exception):
    pass


class UpdateNotificationStatus:
    def __init__(self):
        session = boto3.Session()
        self.dynamodb = session.resource('dynamodb')
        self.ssm = session.client('ssm')

    def discover_resources(self, table):
        response = ''
        try:
            response = table.scan(
                           IndexName='Notifications',
                           FilterExpression=Attr('Notification').eq('false')
                       )
            resources = response['Items']
            while True:
                if response.get('LastEvaluatedKey'):
                    response = table.scan(
                                   IndexName='Notifications',
                                   FilterExpression=(
                                       Attr('Notification').eq('false')
                                   ),
                                   ExclusiveStartKey=(
                                       response['LastEvaluatedKey']
                                   )
                               )
                    resources += response['Items']
                else:
                    break
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error scanning table: %s" % e)
            raise ScanTableException("Error scanning table: %s" % e)

        return resources

    def change_notification(self, table, resources):
        try:
            for resource in resources:
                table.update_item(
                    Key={
                        'ConfigRuleName': resource['ConfigRuleName'],
                        'ResourceId': resource['ResourceId']
                    },
                    UpdateExpression='SET Notification = :v_Flag',
                    ExpressionAttributeValues={
                        ':v_Flag': 'true'
                    }
                )
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error updating item: %s" % e)
            raise UpdateItemException("Error: %s" % e)

    def handler_impl(self, event, context):
        print('Function Name: ' + context.function_name)
        print('Function Version: ' + context.function_version)
        try:
            table_param = self.ssm.get_parameter(
                              Name='/DXC/ConfigService/DynamoDBTableName'
                          )
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error getting SSM parameter: %s" % e)
            raise GetParameterException("Error: %s" % e)
        try:
            table = self.dynamodb.Table(table_param['Parameter']['Value'])
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error accessing DynamoDB table: %s" % e)
            raise GetTableException("Error: %s" % e)
        resources = self.discover_resources(table)
        if len(resources) > 0:
            self.change_notification(table, resources)
        else:
            print("No resource notifications need to be updated.")
