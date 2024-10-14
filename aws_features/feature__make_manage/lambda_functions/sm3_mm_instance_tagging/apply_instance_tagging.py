'''
# Implemented via AWSPE-5779, AWSPE-6010  and AWSPE-6044
# Acceptance Criteria:

This Function is used to add Tags for instance while STEP 3 StateMachineInstanceTagging
'''
import boto3, os
from botocore.config import Config
from boto3.dynamodb.conditions import Key

class instance_tagging():
    def __init__(self, region='us-east-1'):
        self.config = Config(retries=dict(max_attempts=10,mode='standard'))
        self.ec2 = boto3.resource('ec2')
        self.ddb = boto3.resource('dynamodb', config=self.config)
        self.ddb_inst_info = os.environ['ddbInstInfoTableName']
        self.ddb_param_set = os.environ['ddbParamSetTableName']
        self.customer_bucket = os.environ['evDXCS3CustomerBucketName']
        self.region = region

    def exec_instance_tagging(self,instanceId):
        """
        """
        StateDetail = ''
        StateSuccessFail = ''
        try:
            ddb_inst_info_table_obj = self.ddb.Table(self.ddb_inst_info)
            response = ddb_inst_info_table_obj.get_item(Key={
                        'InstanceId': instanceId
                        })
            instance_data = response['Item']
            if instance_data:
                ParameterSetName = instance_data['ParameterSetName']
                osname = instance_data['os-name'].strip()
                osarch = instance_data['os-arch'].strip()
                
                ddb_param_set_table_obj = self.ddb.Table(self.ddb_param_set)
                param_response = ddb_param_set_table_obj.get_item(Key={
                            'ParameterSetName': ParameterSetName
                            })
                param_response_data = param_response['Item']
                param_response_data['OSName'] = osname
                ec2instance = self.ec2.Instance(instanceId)
                for i in ec2instance.tags:
                    if (i['Key'] == 'Name'):
                        param_response_data['InstanceName'] = i['Value']
                for k,v in param_response_data.items():
                    self.ec2.create_tags(Resources=[instanceId], Tags=[{'Key':k, 'Value':v}])
                    StateSuccessFail = 'SUCCESS'
                print("TAGGING Status ", StateDetail,StateSuccessFail) 
                
        except Exception as e:
            StateSuccessFail = 'FAIL'
            StateDetail = str(e)
        return StateDetail,StateSuccessFail