'''
# Implemented via AWSPE-5779, AWSPE-6010  and AWSPE-6044
# Acceptance Criteria:

This Function is used to check if instance is running or STOPPED state  while STEP 3 StateMachineInstanceTagging
If Instance is in STOPPED state then it will be FAILED and moved to STEP 5 StateMachineMMSummaryReport

'''
import boto3, os, time, datetime
from botocore.config import Config
from boto3.dynamodb.conditions import Key
import falcon_command_os_type

class boto_helper():
    def __init__(self, region='us-east-1'):
        self.config = Config(retries=dict(max_attempts=10,mode='standard'))

        self.ec2 = boto3.resource('ec2')
        self.ssm_client = boto3.client('ssm', config=self.config)
        self.ddb = boto3.resource('dynamodb', config=self.config)
        self.ddb_inst_info = os.environ['ddbInstInfoTableName']
        self.ddb_inst_rep = os.environ['ddbInstRepTableName']
        self.ddb_param_set = os.environ['ddbParamSetTableName']
        self.customer_bucket = os.environ['evDXCS3CustomerBucketName']
         
        currentDT = datetime.datetime.now()
        self.date_time= currentDT.strftime('%m_%d_%Y_%H%M%S')
        self.region = region
        

    def install_falcon(self,instanceId,StateName):

        StateDetail = ''
        StateSuccessFail = ''
        instance_output = {}
        try:
            ddb_inst_info_table_obj = self.ddb.Table(self.ddb_inst_info)
            response = ddb_inst_info_table_obj.get_item(Key={
                        'InstanceId': instanceId
                        })
            instance_data = response['Item']
            print(instance_data)
            parametersetname = instance_data['ParameterSetName'].strip()
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
                    if k =='ApplyEndPointProtection' and v:
                        ApplyEndpointProtection = 1
                #Install Falcon
                if ApplyEndpointProtection:
                    print("############################### HARDENING-FALCON INSTALL START #######################")
                    StateDetail,StateSuccessFail = self.exec_instance_endpointProtection(instanceId,osname,self.customer_bucket)
                    print("HARDENING-FALCON INSTALL Status ", StateDetail,StateSuccessFail)
                    print("############################### HARDENING-FALCON INSTALL END #######################")
                instance_output['InstanceId'] = instanceId
                instance_output['CreationTime'] = self.date_time
                instance_output['ModifyTime'] = self.date_time
                instance_output['ParameterSetName'] = parametersetname
                instance_output['StateDetail'] = StateDetail
                instance_output['StateSuccessFail'] = StateSuccessFail
                instance_output['StateName'] = StateName
        except Exception as e:
            print("FINAL ERROR OCCURRED for Installing Falcon: ", str(e))
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

    def getParametervalue(self):
        """
        """
        response = self.ssm_client.get_parameter(Name='CrowdStrikeCID',WithDecryption=True)
        cid=response['Parameter']['Value']
        cid=cid[4:] if 'CID-' in cid.upper() else cid
        return cid

    def exec_instance_endpointProtection(self,instanceId,osname,BUCKET):
        """
        """
        StateDetail = ''
        StateSuccessFail = ''
        CrowdStrikeCID = self.getParametervalue()
        try:
            osbased_command_dict = {  "AMAZON-LINUX2" : falcon_command_os_type.amazonlinux_falcon_command.format(BUCKET),
                                      "AMAZON-LINUX": falcon_command_os_type.amazonlinux_falcon_command.format(BUCKET),
                                      "RHEL": falcon_command_os_type.rhel_falcon_command.format(BUCKET),
                                      "UBUNTU": falcon_command_os_type.ubuntu_falcon_command.format(BUCKET),
                                      "SUSE": falcon_command_os_type.suse_falcon_command.format(BUCKET),
                                      "ORACLE": falcon_command_os_type.oracle_falcon_command.format(BUCKET),
                                      "WINDOWS": falcon_command_os_type.windows_falcon_command.format(BUCKET,self.region,CrowdStrikeCID)
                                    }
            print("Command Syntax Validation passed")
        except Exception as e:
            print('Error exec_instance_endpointProtection() ',str(e))
                                    
        waiter = self.ssm_client.get_waiter('command_executed')
        if osname == "WINDOWS":
            DocumentName = "AWS-RunPowerShellScript"
        else:
            DocumentName = "AWS-RunShellScript"
        falconosbased_command =  osbased_command_dict[osname]
        print("######################## FALCON COMMAND START HERE##################################")
        print(falconosbased_command)
        print("######################## FALCON COMMAND END HERE##################################")
        response = self.ssm_client.send_command(
            InstanceIds=[instanceId],
            DocumentName=DocumentName,
            Parameters={'commands': [falconosbased_command]}, )   

        try:
            send_cmd_attempt = 0
            while True:
                send_cmd_attempt += 1
                try:  
                    command_id = response['Command']['CommandId']
                    print('response:',response)
                    print('command_id:',command_id)
                    waiter.wait(
                        CommandId=command_id,
                        InstanceId=instanceId,
                        #PluginName='string',
                        WaiterConfig={
                            'Delay': 100,
                            'MaxAttempts': 10
                        }
                    )
                    time.sleep(30)
                    output = self.ssm_client.get_command_invocation(
                        CommandId=command_id,
                        InstanceId=instanceId)
                    print('output:',output)
                    status = output['Status']
                    print(send_cmd_attempt,status)
                    if(status in ['InProgress','Pending'] and send_cmd_attempt <=5):
                        time.sleep(30)
                    elif(status== 'Success'):
                        StateSuccessFail = 'SUCCESS'
                        return StateDetail,StateSuccessFail
                except Exception as e:
                    print('send_cmd_attempt - ',send_cmd_attempt)
                    print('Exception occurred for exec_instance_endpointProtection() -',str(e))
                    StateDetail = str(e)
                    print(StateDetail)                 
        except Exception as e:
            print('Error exec_instance_endpointProtection() ',str(e))
            StateDetail = str(e)
            StateSuccessFail = 'FAIL'
        print(StateDetail,StateSuccessFail)
        return StateDetail,StateSuccessFail