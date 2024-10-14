'''
Boto Helper class contain all the supported aws api operations required to perform backup operation
'''
import boto3
from botocore.config import Config
import json
from datetime import datetime

class boto_helper():

    def __init__(self):
        self.config = Config(retries=dict(max_attempts=10,mode='standard'))
        self.ddb = boto3.resource('dynamodb', config=self.config)
        self.ddb_client = boto3.client('dynamodb', config=self.config)
        self.state_client = boto3.client('stepfunctions', config = self.config)
        self.log_client = boto3.client('logs', config = self.config)
        self.cw_client = boto3.client('cloudwatch',config = self.config)
            
    #Checking whether the alarm is available or not.
    def alarm_check(self,alarm_name):
        try:
            response = self.cw_client.describe_alarms(AlarmNamePrefix=alarm_name)
            alarmlist = (response.get('MetricAlarms')[0].get('AlarmName'))
            print('"{}" alarm already exists'.format(alarm_name)) 
            return alarmlist    
        except:
            print('"{}" alarm NOT exists'.format(alarm_name)) 
            return
        
    # To create an cloudwatch alarm
    def create_alarm(self, metrics, request='Create'):
        try:
            input_metrics = {}
            if('AlarmName' in metrics): input_metrics['AlarmName'] = metrics['AlarmName']
            if('AlarmActions' in metrics): input_metrics['AlarmActions'] = metrics['AlarmActions']
            if('ActionsEnabled' in metrics): input_metrics['ActionsEnabled'] = metrics['ActionsEnabled']
            if('AlarmDescription' in metrics): input_metrics['AlarmDescription'] = metrics['AlarmDescription']
            if('ComparisonOperator' in metrics): input_metrics['ComparisonOperator'] = metrics['ComparisonOperator']
            if('Dimensions' in metrics): input_metrics['Dimensions'] = metrics['Dimensions']
            if('EvaluationPeriods' in metrics): input_metrics['EvaluationPeriods'] = int(metrics['EvaluationPeriods'])
            if('MetricName' in metrics): input_metrics['MetricName'] = metrics['MetricName']
            if('Namespace' in metrics): input_metrics['Namespace'] = metrics['Namespace']
            if('Period' in metrics): input_metrics['Period'] = int(metrics['Period'])
            if('Statistic' in metrics): input_metrics['Statistic'] = metrics['Statistic']
            if('Threshold' in metrics): input_metrics['Threshold'] = int(metrics['Threshold'])
            
            print(input_metrics)
            self.cw_client.put_metric_alarm(**input_metrics)
            print('Alarm - "{}" {}d successfully'.format(input_metrics['AlarmName'], request))
        except Exception as e:
            print('Error create_alarm()-',e)
            raise
    
    #To get the metrics of the existing alarm        
    def get_alarm(self, alarm_name):
        try:
            response = self.cw_client.describe_alarms(
                AlarmNames=[alarm_name])
            return response['MetricAlarms'][0] if(len(response['MetricAlarms'])) else False
        except Exception as e:
            print('Erro chk_get_alarm_exists()-',e)
            raise