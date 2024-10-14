#
# Send message to SNS topic notifying which AWS resources
# are non-compliant. Resources are pulled from DynamoDB table
#
# Trigger Type: Step Function State [SendNotification]
# Scope: Non-Compliant Resources in AWS Config
# Accepted Parameter: None
#

from __future__ import print_function
from boto3.dynamodb.conditions import Attr
import boto3
import json
import os
from boto3.dynamodb.conditions import Key, Attr
from botocore.config import Config
import datetime
import copy

class GetParameterException(Exception):
    pass


class GetTableException(Exception):
    pass


class ScanTableException(Exception):
    pass


class SNSNotificationException(Exception):
    pass


class SendNotification:
    def __init__(self):
        session = boto3.Session()
        self.dynamodb = session.resource('dynamodb')
        self.sns = session.client('sns')
        self.ssm = session.client('ssm')
        self.account_id = None
        self.alarm_name = None
        config=Config(retries=dict(max_attempts=10,mode='standard'))
        self.ddb = boto3.resource('dynamodb', config=config)
        self.table = self.ddb.Table('AccountFeatureDefinitions')
        self.currentDT = datetime.datetime.now()
        self.Date_time= self.currentDT.strftime("%Y%m%d_%H%M%S")
        self.val_to_fetch = 'pfSnowInciPriority'
        self.feature_name = 'ConfigNotificationService'
        self.whitelisting_rule="FeatureConfigRuleS3PublicRead"
        self.whitelistedSSMParam=os.environ["WhitelistedSSMParam"]
        self.DynamodbParam=os.environ["DynamoDBParam"]

    def discover_resources(self, table):
        resources = ''
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

    # method will read the data from ADS Dynamo Db table to get the object
    def get_db_object(self,table,feature_name,val_to_fetch):
        try:
            response = table.query(KeyConditionExpression=Key('Feature').eq(feature_name))

            for item in response['Items']:
                fetched_object = item['FeatureParams'][val_to_fetch]['Default']
                print('fetched_object:',fetched_object)

            return fetched_object
        except Exception as e:
            print('error in get_db_object():',e)
            raise

    def send_notification_to_snow(self,resources,snow_topic):
        if len(resources) > 0:
            alarm_description = "Non-Compliant Resources: " + str(resources)
            print(alarm_description)
            priority_val =  self.get_db_object(self.table,self.feature_name,self.val_to_fetch)
            eventsourcesendingserver = 'Feature__config_notification_service'
            application = "Feature__config_notification_service : - " + str(self.Date_time)
            long_desc = "Non-Compliant Resources: " + str(resources)
            incidentTitle = "Non-Compliant Config Resources : - " + str(self.Date_time)
            message = {
                        "EventList":[
                        {
                            "Trigger": {
                                "MetricName": "Config Service: Non-Compliance",
                                "EvaluateLowSampleCountPercentile": "",
                                "ComparisonOperator": "GreaterThanThreshold",
                                "TreatMissingData": "",
                                "Statistic": "SampleCount",
                                "StatisticType": "Statistic",
                                "Dimensions": [],
                                "Period": 3600,
                                "EvaluationPeriods": 1,
                                "Namespace": "ConfigEvaluations",
                                "Threshold": 0,
                                "Region": os.environ['AWS_REGION']
                            },
                            "AlarmName": self.alarm_name,
                            "AlarmDescription": "Non-Compliant Config Resources",
                            "AWSAccountId": self.account_id,
                            "OldStateValue": "OK",
                            "NewStateValue": "ALARM",
                            "NewStateReason": alarm_description,
                            "eventsourcesendingserver": eventsourcesendingserver,
                            "eventsourceexternalid": self.Date_time,
                            "title": incidentTitle,
                            "longDescription": long_desc,
                            "application": application,
                            "eventsourcecreatedtime": self.Date_time,
                            "PriorityData": {
                                "Priority": priority_val
                            }
                        }    
                        ] 
                    }
            try:
                result = self.sns.publish(
                                TopicArn=snow_topic,
                                Message=json.dumps(
                                            {'default': json.dumps(message)}
                                        ),
                                MessageStructure='json',
                                Subject=('AWS Config Notification Service')
                            )
                print(result)            
            except Exception as e:
                print('error in send_to_snow():',e)
                raise
        else:
            print("Notification does not need to be sent.")

    def set_delivery_status(self, context, topic_arn):
        response = self.sns.get_topic_attributes(TopicArn=topic_arn)
        try:
            #Check to see if SNS dlivery status has been set
            if not response['Attributes'].get('HTTPSuccessFeedbackRoleArn'):
                self.sns.set_topic_attributes(
                    TopicArn=topic_arn,
                    AttributeName='HTTPSuccessFeedbackRoleArn',
                    AttributeValue=os.environ['SNSFeedbackRoleArn']
                )
                self.sns.set_topic_attributes(
                    TopicArn=topic_arn,
                    AttributeName='HTTPFailureFeedbackRoleArn',
                    AttributeValue=os.environ['SNSFeedbackRoleArn']
                )
                print('SNS Delivery status Enabled')

        except boto3.exceptions.botocore.client.ClientError as e:
            print("Not able to set SNS Delivery Status roles: %s" % e)
            raise SNSNotificationException("Error: %s" % e)

    def remove_whitelisted_items(self,resources):
        try:
            try:
                whitelisted_resources=(self.ssm.get_parameter(Name=self.whitelistedSSMParam)['Parameter']['Value']).split(",")
                if "AWSPE-NOVALUE" in whitelisted_resources[0].upper() and len(whitelisted_resources)==1:
                    raise
            except:
                print("There are no whitelisted resources!")
                comment="Incident creation initiated in ServiceNow"
                self.update_comments(resources,comment)
                return resources
            all_resources=copy.deepcopy(resources)
            for resource in resources:
                if resource['ResourceId'] in whitelisted_resources and self.whitelisting_rule in  resource['ConfigRuleName']:
                    all_resources.remove(resource)
                    print("removed whitelisted resource '{}' from ServiceNow alert".format(resource['ResourceId']))
                    comment="Not creating incident, whitelisted in {}".format(self.whitelistedSSMParam)
                    self.update_comments([resource],comment)
                else:
                    comment="Incident creation initiated in ServiceNow"
                    self.update_comments([resource],comment)
            return all_resources
        except Exception as e:
            ("Error-remove_whitelisted_items()",e)
            
    def update_comments(self,resources,comment):
        try:
            table_param = self.ssm.get_parameter(Name=self.DynamodbParam)
            table = self.ddb.Table(table_param['Parameter']['Value'])
            for resource in resources:
                table.update_item(
                        Key={
                            'ConfigRuleName': resource['ConfigRuleName'],
                            'ResourceId': resource['ResourceId']
                        },
                        UpdateExpression='SET Comments = :com',
                        ExpressionAttributeValues={
                            ':com': comment
                        }
                    )
        except Exception as e:
            print("Error-update_comments()",e)

    def handler_impl(self, event, context):
        print('Function Name: ' + context.function_name)
        print('Function Version: ' + context.function_version)
        self.account_id = context.invoked_function_arn.split(':')[4]
        self.alarm_name = context.function_name
        snow_topic = os.environ['SnowTopic']
        try:
            table_param = self.ssm.get_parameter(
                              Name='/DXC/ConfigService/DynamoDBTableName'
                          )
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error accessing SSM parameter: %s" % e)
            raise GetParameterException("Error: %s" % e)
        try:
            table = self.dynamodb.Table(table_param['Parameter']['Value'])
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error accessing DynamoDB table: %s" % e)
            raise GetTableException("Error: %s" % e)
        self.set_delivery_status(context, snow_topic)
        resources = self.discover_resources(table)
        resources=self.remove_whitelisted_items(resources)
        self.send_notification_to_snow(resources,snow_topic)
