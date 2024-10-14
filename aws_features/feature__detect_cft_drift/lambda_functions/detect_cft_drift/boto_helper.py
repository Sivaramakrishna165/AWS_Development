import boto3, json
from operator import itemgetter
from botocore.config import Config

class boto_helper():
    def __init__(self):
        config=Config(retries=dict(max_attempts=10,mode='standard'))
        self.ssm_client = boto3.client('ssm',config=config)
        self.secmgr_client = boto3.client('secretsmanager',config=config)
        self.cf_client = boto3.client('cloudformation',config=config)
        self.sns_client = boto3.client('sns',config=config)
        self.events_client = boto3.client('events',config=config)
        self.dynamodb_resource=boto3.resource('dynamodb', config=config)

    def get_all_stacks(self):
        stacks = []
        try:
            extra_args = {}
            extra_args['StackStatusFilter']=['CREATE_COMPLETE','UPDATE_COMPLETE', 'UPDATE_ROLLBACK_COMPLETE']
            while True:
                response = self.cf_client.list_stacks(**extra_args)
                stacks.extend(list(map(itemgetter('StackName'), response['StackSummaries'])))            
                if 'NextToken' in response:
                    extra_args['NextToken'] = response['NextToken'] 
                else:
                    break            
        except Exception as e:
            print('Error get_all_stacks() - ',str(e))
        finally:
            return stacks
        
    def get_managed_stacks(self, stack_names):
        print('Getting Managed Stacks process started')
        managedstacks = []
        try:
            for stack in stack_names:
                stack_response = self.cf_client.describe_stacks(StackName=stack)
                tag = stack_response['Stacks'][0]['Tags']
                
                tagging={}
                for i in tag:
                    tagging[i['Key']]=i['Value']
                    
                if 'Owner' in tagging and 'Application' in tagging:
                    if tagging['Owner'] == 'DXC' and tagging['Application'] == 'AWS Managed Services':
                        managedstacks.append(stack)
                    else:
                        print('The stack {} is not part of the Managed Services'.format(stack))
                else:
                    print('The stack {} is not part of the Managed Services'.format(stack))
                            
        except Exception as e:
            print('Error get_managed_stacks() - ',str(e))
            
        finally:
            return managedstacks        
        
    def describe_stack_resource_drifts(self, stack_name, drift_filter=['MODIFIED','DELETED'], white_listed_resources = None):
        try:
            drifted_resources = []
            extra_args = {}
            extra_args['StackName'] = stack_name
            extra_args['StackResourceDriftStatusFilters'] = drift_filter
            while True:
                response = self.cf_client.describe_stack_resource_drifts(**extra_args)
                for drft_res in response['StackResourceDrifts']:
                    if drft_res['PhysicalResourceId'] not in white_listed_resources:
                        drifted_resources.append(
                            {
                            'PhysicalResourceId' : drft_res['PhysicalResourceId'],
                            'ResourceType' : drft_res['ResourceType'],
                           'StackResourceDriftStatus' : drft_res['StackResourceDriftStatus']
                           })
    
                if 'NextToken' in response:
                    extra_args['NextToken'] = response['NextToken']
                else:
                    break            
        
        except Exception as e:
            print('Error describe_stack_resource_drifts() - ',e)
        finally:
            return drifted_resources            
    
    def detect_drift(self, stack_name):
        try:
            detection_id = self.cf_client.detect_stack_drift(StackName=stack_name)['StackDriftDetectionId']
            print('Detect drift executed - {} detection_id - {}'.format(stack_name, detection_id))
        except Exception as e:
            print('Error detect_drift() - ',e)
    
    def get_secrets(self, secret_name):
        try:
            get_secret_value_response = self.secmgr_client.get_secret_value(
                SecretId=secret_name
            )
            secret_dict = json.loads(get_secret_value_response['SecretString'])
            return secret_dict
        except Exception as e:
            print('Error get_secrets() - ',e)
        
    def get_ssm_param_values(self, ssm_param = None):    
        try:
            response = self.ssm_client.get_parameter(Name=ssm_param)
            return response['Parameter']['Value']
        except self.ssm_client.exceptions.ParameterNotFound:
            raise(Exception('SSM Parameter Not found - {}'.format(ssm_param)))
        except Exception as e:
            print('get_ssm_param_values() error:', e)
    
    # Publish the given message to the topic.
    def publish_to_topic(self, topic, event, account, region,servicenow=False):
        try:
            
            if servicenow:
                self.sns_client.publish(
                Message=event,
                TopicArn=topic
                )
                print('Notification published successfully, subscription_type - Servicenow Topic')
            else:
                message = """AWSMS Offerings - Detect Cloudformation drifts\n"""
                snsJson = {}
                snsJson['default'] = message
                snsJson['email'] = json.dumps({'CFT-Drifts': event})
                snsJson['https'] = json.dumps(event)
                snsJsonMsg = json.dumps(snsJson)
                self.sns_client.publish(
                MessageStructure='json',
                Message=snsJsonMsg,
                Subject='AWSMS Offerings - Detect CFT Drift alert - Account: {} Region: {}'.format(account,region),
                TopicArn=topic
                )
                print('Notification published successfully, subscription_type - EMAIL')
        except Exception as e:
            print('Error - publish_to_topic() - ',e)

    def enable_event_rule(self, rule_name):
        try:
            self.events_client.enable_rule(Name=rule_name)
        except Exception as e:
            print('Error - enable_rule() ',e)

    def disable_event_rule(self, rule_name):
        try:
            self.events_client.disable_rule(Name=rule_name)
        except Exception as e:
            print('Error - disable_event_rule() ',e)
    
    def fetch_priority(self):
        try:
            
            table = self.dynamodb_resource.Table('AccountFeatureDefinitions')
            response = table.get_item(Key={"Feature":"DetectCftDrift"})
            priority = response['Item']['FeatureParams']['pDetectDriftIncidentsPriority']['Default']
            return priority
        except Exception as e:
            print("Error-getting priority-",e)