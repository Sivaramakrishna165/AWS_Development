"""
This lambda is creating a common Invocation and Throttle alarms for all lambda function. 
sample input : 
                {
                    "alarm_action": "arn:aws:sns:ap-southeast-1:567529657087:sample_sns_topic",
                    "data_points": 1,
                    "disable_static_alarm": False,
                    "evalution_period": 1,
                    "expression": "ANOMALY_DETECTION_BAND(m1, 2)",
                    "metric_name": "Invocation/Throttle",
                    "s3_bucket": "dxc.customer.config-567529657087-ap-southeast-1"
                }
"""
import boto3
from botocore.config import Config
import os

config=Config(retries=dict(max_attempts=10,mode='standard'))

dynamodb_resource = boto3.resource('dynamodb',config=config)

cloudwatch = boto3.client('cloudwatch',config=config)

table_name = os.environ['table_name']

def get_data(Metric_name):
    table = dynamodb_resource.Table(table_name)
    response = ''
    try:
        item_dict = { 
        'Metric Name': Metric_name
        } 
        response = table.get_item(
            Key=item_dict
        )
        print(response)
    except Exception as e:
        response = ''
        print("Error get_data() - ",e)
    return response

def create_ad_alarms(band,datappoints,evalution_period,period,Metric_name,topic_arn):
    try:
        cloudwatch.put_metric_alarm(
            AlarmName='ad_alerts_'+Metric_name,
            AlarmDescription="this is dynamic alarm",
            ActionsEnabled=True,
            AlarmActions=[
                topic_arn],
            EvaluationPeriods=evalution_period,
            DatapointsToAlarm=datappoints,
            ComparisonOperator='GreaterThanUpperThreshold',
            TreatMissingData='missing',
            Metrics=[{
                'Id': 'm1',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/Lambda',
                        'MetricName': Metric_name
                    },
                    'Period': period,
                    'Stat': "Sum"
                },
                'ReturnData': True
            }, {
                'Id': 'ad1',
                'Expression': 'ANOMALY_DETECTION_BAND(m1, '+band+')',
                'ReturnData': True
            }],
            ThresholdMetricId='ad1'
        )
        print("alarm created for ",Metric_name)

    except Exception as e:
        print("unable to proceed : ",e)

def lambda_handler(event, context):
    try:
        print('Received event is ',event)
        metric_names = ['Invocations','Throttles']
        for metric_name in metric_names:
            response = get_data(metric_name)
            band = response['Item']['Band']
            datappoints = int(response['Item']['Data Points'])
            evalution_period = int(response['Item']['Evalution Period'])
            period = int(response['Item']['Period'])
            Metric_name = response['Item']['Metric Name']
            topic_arn = response['Item']['SNS Topic ARN']
            create_ad_alarms(band,datappoints,evalution_period,period,Metric_name,topic_arn)
    except Exception as e:
        print("Error lambda_handler() - ",e)
    return event