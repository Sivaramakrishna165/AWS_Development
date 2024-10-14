
'''
# Implemented via AWSPE-5779, AWSPE-6010  and AWSPE-6044
# Acceptance Criteria:

This Function is used to check if instance is running or STOPPED state  while STEP 3 StateMachineInstanceTagging
If Instance is in STOPPED state then it will be FAILED and moved to STEP 5 StateMachineMMSummaryReport

'''
import boto3, os, datetime
from botocore.config import Config
from boto3.dynamodb.conditions import Key
from apply_instance_tagging import instance_tagging

class checkinstancerunning():
    def __init__(self, region='us-east-1'):
        self.config = Config(retries=dict(max_attempts=10,mode='standard'))

        self.ec2_resource = boto3.resource('ec2')
        self.ddb = boto3.resource('dynamodb', config=self.config)
        self.ddb_inst_info = os.environ['ddbInstInfoTableName']
        self.ddb_inst_rep = os.environ['ddbInstRepTableName']
        self.ddb_param_set = os.environ['ddbParamSetTableName']

        currentDT = datetime.datetime.now()
        self.date_time= currentDT.strftime('%m_%d_%Y_%H%M%S')
        self.region = region

    def excheck_instance_running(self,instanceId,StateName):
        """
        """
        StateDetail = ''
        StateSuccessFail = ''
        instance_output = {}
        parametersetname = ''
        try:
            ddb_inst_info_table_obj = self.ddb.Table(self.ddb_inst_info)
            response = ddb_inst_info_table_obj.get_item(Key={
                        'InstanceId': instanceId
                    })
            instance_data = response['Item']
            print(instance_data)
            parametersetname = instance_data['ParameterSetName'].strip()
            instance = self.ec2_resource.Instance(instanceId)
            if instance.state['Name']:
                if instance.state['Name'] !='running':
                    instance_output['InstanceId'] = instanceId
                    instance_output['CreationTime'] = self.date_time
                    instance_output['ModifyTime'] = self.date_time
                    instance_output['ParameterSetName'] = parametersetname
                    instance_output['StateDetail'] = 'Error Occurred as instance is in' + str(instance.state['Name']) + 'state'
                    instance_output['StateSuccessFail'] = 'FAIL'
                    instance_output['StateName'] = StateName
                else:
                    instance_tagging_obj = instance_tagging(self.region)
                    StateDetail,StateSuccessFail = instance_tagging_obj.exec_instance_tagging(instanceId)  
                    instance_output['InstanceId'] = instanceId
                    instance_output['CreationTime'] = self.date_time
                    instance_output['ModifyTime'] = self.date_time
                    instance_output['ParameterSetName'] = parametersetname
                    instance_output['StateDetail'] = StateDetail
                    instance_output['StateSuccessFail'] = StateSuccessFail
                    instance_output['StateName'] = StateName 
        except Exception as e:
            print("FINAL ERROR OCCURRED for instance Tagging : ", str(e))
            StateSuccessFail = 'FAIL'
            StateDetail = str(e)
            instance_output['InstanceId'] = instanceId
            instance_output['CreationTime'] = self.date_time
            instance_output['ModifyTime'] = self.date_time
            instance_output['ParameterSetName'] = parametersetname
            instance_output['StateDetail'] = StateDetail
            instance_output['StateSuccessFail'] = StateSuccessFail
            instance_output['StateName'] = StateName
        print(instance_output)
        if(instance_output):
            self.insertToReportsTables(instance_output)
        return instance_output 

    def insertToReportsTables(self,instance_output):
        try:
            ddb_inst_rep_table_obj = self.ddb.Table(self.ddb_inst_rep)
            ddb_inst_rep_table_obj.put_item(Item=instance_output)
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error adding item: {}  - {}".format(instance_output, str(e)))
            raise   