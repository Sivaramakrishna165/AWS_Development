'''
# Implemented via AWSPE-5777
# Acceptance Criteria:

STEP 1 StateMachineSSMInstall

This funtion is used to Install SSM for the ec2 instances information provided in the 
Dynamodb table FtMakeManageInstancesInfo will take input of instance details
Execute verification of SSM installed if not installed then install it otherwise proceed for next step
And this function is invoked by the make-manage step function

Based on the InstanceId and osname values will be pulled from DynamoDB table,
the exec_install_ssm() gets & constructs the required information for 
executing the SSM template.

'''
import base64
import boto3, os, datetime,time
from botocore.config import Config
import ssm_command_list_os_based

class install_ssm():
    def __init__(self, region='us-east-1'):
        self.config = Config(retries=dict(max_attempts=10,mode='standard'))
        x86_64_arch_key = "x86_64"
        arm_arch_key = "Arm"
        x86_64_arch = "amd64"
        arm_arch = "arm64"
        self.region = region
        self.ssm_install_command_dict = { "AMAZON-LINUX2_{}".format(x86_64_arch_key) : ssm_command_list_os_based.amzlinux2_ssm_command.format(self.region,self.region,x86_64_arch),
                                          "AMAZON-LINUX2_{}".format(arm_arch_key) : ssm_command_list_os_based.amzlinux2_ssm_command.format(self.region,self.region,arm_arch),
                                          "AMAZON-LINUX_{}".format(x86_64_arch_key) : ssm_command_list_os_based.amzlinux2_ssm_command.format(self.region,self.region,x86_64_arch),
                                          "AMAZON-LINUX_{}".format(arm_arch_key) : ssm_command_list_os_based.amzlinux2_ssm_command.format(self.region,self.region,arm_arch),
                                          "RHEL_{}".format(x86_64_arch_key) : ssm_command_list_os_based.rhel_ssm_command.format(self.region,self.region,x86_64_arch),
                                          "RHEL_{}".format(arm_arch_key) : ssm_command_list_os_based.rhel_ssm_command.format(self.region,self.region,arm_arch),
                                          "UBUNTU_{}".format(x86_64_arch_key) : ssm_command_list_os_based.ubuntu_ssm_command.format(self.region,self.region,x86_64_arch),
                                          "UBUNTU_{}".format(arm_arch_key) : ssm_command_list_os_based.ubuntu_ssm_command.format(self.region,self.region,arm_arch),
                                          "SUSE_{}".format(x86_64_arch_key): ssm_command_list_os_based.suse_ssm_command.format(self.region,self.region,x86_64_arch),
                                          "SUSE_{}".format(arm_arch_key): ssm_command_list_os_based.suse_ssm_command.format(self.region,self.region,arm_arch),
                                          "ORACLE_{}".format(x86_64_arch_key): ssm_command_list_os_based.oracle_ssm_command.format(self.region,self.region,x86_64_arch),
                                          "ORACLE_{}".format(arm_arch_key): ssm_command_list_os_based.oracle_ssm_command.format(self.region,self.region,arm_arch),
                                          "WINDOWS_{}".format(x86_64_arch_key) : ssm_command_list_os_based.windows_ssm_command
                                        }

        currentDT = datetime.datetime.now()
        self.date_time= currentDT.strftime('%m_%d_%Y_%H%M%S')
        self.ec2_resource = boto3.resource('ec2',region_name=region, config=self.config)
        self.ec2_client = boto3.client('ec2',region_name=region, config=self.config)
        self.ddb = boto3.resource('dynamodb', config=self.config)
        self.ddb_inst_info = os.environ['ddbInstInfoTableName']
        self.ddb_inst_rep = os.environ['ddbInstRepTableName']
        self.ddb_param_set = os.environ['ddbParamSetTableName']

    def getInstanceUserData(self,instanceid):
        for instance in self.ec2_resource.instances.all():
            if instance.id == instanceid:
                response = instance.describe_attribute(Attribute='userData')
                if 'UserData' in response and response['UserData']:
                    extuserdata = response['UserData']['Value']
                    return extuserdata

    def installSSMUsingUserData(self,instanceid,os_info,extuserdata,osname):
        """
        Install SSM Using User data
        """
        StateDetail = ''
        StateSuccessFail = ''
        try:
            print("##################### START #######################")
            userdatavalue = ''
            if osname == "WINDOWS":
                ssmcommandfile = self.ssm_install_command_dict[os_info]
                userdatavalue = ssmcommandfile.lstrip()
            else:
                print("ssmcommandfile execute started for ",os_info)
                ssmcommandfile = ssm_command_list_os_based.common_ssm_command + self.ssm_install_command_dict[os_info]
                print(ssmcommandfile)
                if extuserdata:
                    userdatavalue = extuserdata + "\n" + ssmcommandfile.lstrip()
                else:
                    userdatavalue = ssmcommandfile.lstrip()       

            userdatavalue = base64.b64encode(userdatavalue.encode()).decode("ascii")
            self.ec2_client.modify_instance_attribute(InstanceId=instanceid, Attribute='userData', Value=userdatavalue.lstrip())
            StateSuccessFail = "SUCCESS"
            print("##################### END #######################")
        except Exception as e:
            Error_Message  = "Failed to update UserData (could be wrong OS Name/OS Arch/Invalid Command/Empty UserData ) : " + str(e)
            StateSuccessFail = 'FAIL'
            StateDetail = Error_Message
            print(Error_Message)
        return StateDetail,StateSuccessFail 

    def insertToReportsTables(self,instance_output):
        try:
            ddb_inst_rep_table_obj = self.ddb.Table(self.ddb_inst_rep)
            # print(ddb_inst_rep_table_obj)
            ddb_inst_rep_table_obj.put_item(Item=instance_output)
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error adding item: {}  - {}".format(instance_output, str(e)))
            raise

    def updateOriginalUserData(self,instanceid,extuserdata):
        StateDetail = ''
        StateSuccessFail = ''
        try:
            print("##################### START #######################")
            userdatavalue = "echo \"Update User Data\"\n"  # add one charcter empty space otherise An error occurred (MissingParameter) when calling the ModifyInstanceAttribute operation: The request must contain the parameter value 
            if extuserdata:
                userdatavalue = extuserdata
            userdatavalue = base64.b64encode(userdatavalue.encode()).decode("ascii")
            self.ec2_client.modify_instance_attribute(InstanceId=instanceid, Attribute='userData', Value=userdatavalue)
            StateSuccessFail = "SUCCESS"
            print("##################### END #######################")
        except Exception as e:
            Error_Message  = "Failed to update Original UserData (could be Empty UserData/Invalid Command ) : " + str(e)
            StateSuccessFail = 'FAIL'
            StateDetail = Error_Message
            print(Error_Message)
        return StateDetail,StateSuccessFail 

    def execInstanceAction(self,instanceId,STATE_NAME):
        """
        """
        waiter = self.ec2_client.get_waiter(STATE_NAME)
        try:
            response  = waiter.wait(
                InstanceIds=[
                    instanceId,
                ],
                DryRun=False,
                WaiterConfig={
                    'Delay': 15,
                    'MaxAttempts': 40
                }
            )
        except Exception as e:
            status_message = e
            print(status_message)

    def run_install_ssm(self,instance_id,osname,osarch,parametersetname):
        """
        """
        StateName = "InstallSSM"
        StateDetail = ''
        StateSuccessFail = ''
        try:
            instance_output = {}
            print("Executation started For InstanceId set to {} for Region {} with OS Name {} with OS Arch {}".format(instance_id,self.region,osname,osarch))
            instance = self.ec2_resource.Instance(instance_id)
            isRunninginstance = 0
            if instance.state['Name']:
                if instance.state['Name'] !='running':
                    instance_output['InstanceId'] = instance_id
                    instance_output['CreationTime'] = self.date_time
                    instance_output['ModifyTime'] = self.date_time
                    instance_output['ParameterSetName'] = parametersetname
                    instance_output['StateDetail'] = 'Error Occurred as instance is in ' + str(instance.state['Name']) + ' state'
                    instance_output['StateSuccessFail'] = 'FAIL'
                    instance_output['StateName'] = StateName
                    if(instance_output):
                        self.insertToReportsTables(instance_output)
                    return instance_output
                else:
                    ssminstalled = self.check_ssm_status(instance_id,osname)
                    print("Check SSM Install Command :", ssminstalled)
                    if ssminstalled:
                        instance_output['InstanceId'] = instance_id
                        instance_output['CreationTime'] = self.date_time
                        instance_output['ModifyTime'] = self.date_time
                        instance_output['ParameterSetName'] = parametersetname
                        instance_output['StateDetail'] = 'SSM IS ALREADY INSTALLED'
                        instance_output['StateSuccessFail'] = 'SUCCESS'
                        instance_output['StateName'] = StateName
                        if(instance_output):
                            self.insertToReportsTables(instance_output)
                        return instance_output
                    isRunninginstance = 1
                    self.ec2_client.stop_instances(InstanceIds=[instance_id])
                    self.execInstanceAction(instance_id,'instance_stopped')
                    instance = self.ec2_resource.Instance(instance_id)
                    print("STOP instance completed",instance.state['Name'])
                extuserdata = self.getInstanceUserData(instance_id)
                print("###################### extuserdata Before install START #######################")
                print(extuserdata)
                print("###################### extuserdata Before install END #########################")
                os_info = osname + '_' + osarch
                if instance.state['Name'] =='stopped':      
                    StateDetail,StateSuccessFail = self.installSSMUsingUserData(instance_id,os_info,extuserdata,osname)
                    print("Update User data with SSM Command : " , StateSuccessFail)

                self.ec2_client.start_instances(InstanceIds=[instance_id])
                self.execInstanceAction(instance_id,'instance_running')
                instance = self.ec2_resource.Instance(instance_id)
                print("START instance completed :",instance.state['Name'])

                self.ec2_client.stop_instances(InstanceIds=[instance_id])
                self.execInstanceAction(instance_id,'instance_stopped')
                instance = self.ec2_resource.Instance(instance_id)
                print("STOP instance completed :",instance.state['Name'])

                if instance.state['Name'] =='stopped':
                    print("###################### extuserdata Before UPDATE START #######################")
                    print(extuserdata)
                    print("###################### extuserdata Before UPDATE END #########################")
                    if extuserdata:
                        StateDetail,StateSuccessFail =  self.updateOriginalUserData(instance_id,extuserdata)
                        print("Update to Original User data : " , StateSuccessFail)
                    self.ec2_client.start_instances(InstanceIds=[instance_id])
                if isRunninginstance and instance.state['Name'] !='running':
                    self.execInstanceAction(instance_id,'instance_running')
                    instance = self.ec2_resource.Instance(instance_id)
                    print("Back to Running state :",instance.state['Name'])
                instance_output['InstanceId'] = instance_id
                instance_output['CreationTime'] = self.date_time
                instance_output['ModifyTime'] = self.date_time
                instance_output['ParameterSetName'] = parametersetname
                instance_output['StateDetail'] = StateDetail
                instance_output['StateSuccessFail'] = StateSuccessFail
                instance_output['StateName'] = StateName
        except Exception as e:
            print("FINAL ERROR OCCURRED for SSM Installed: ", str(e))
            StateSuccessFail = 'FAIL'
            StateDetail = str(e)
            instance_output['InstanceId'] = instance_id
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

    def check_ssm_status(self,instanceid,osname):
        """
        """
        ssm_status_command_dict = { "AMAZON-LINUX2" : "sudo systemctl status amazon-ssm-agent",
                                    "AMAZON-LINUX": "sudo systemctl status amazon-ssm-agent",
                                    "RHEL": "sudo systemctl status amazon-ssm-agent",
                                    "UBUNTU": "sudo systemctl status snap.amazon-ssm-agent.amazon-ssm-agent.service",
                                    "SUSE": "sudo systemctl status amazon-ssm-agent",
                                    "WINDOWS": "Get-Service AmazonSSMAgent",
                                    "ORACLE": "sudo systemctl status amazon-ssm-agent"
                                }
        ssm_boto_client = boto3.client('ssm',config= self.config) 
        ssmcommand = ssm_status_command_dict[osname]
        try:
            status = ''
            send_cmd_attempt = 0
            ssminstalled = 0
            while True:
                send_cmd_attempt += 1
                try:
                    instance = self.ec2_resource.Instance(instanceid)
                    print("Check instance status Before Execute SSM Command", instance.state['Name'])
                    if osname == "WINDOWS":
                        DocumentName = "AWS-RunPowerShellScript"
                    else:
                        DocumentName = "AWS-RunShellScript" 
                    response = ssm_boto_client.send_command(
                                InstanceIds=[instanceid],
                                DocumentName=DocumentName,
                                Parameters={'commands': [ssmcommand]}, )
                    print(response)
                    command_id = response['Command']['CommandId']
                    attempt = 0
                    while True:
                        attempt += 1
                        output ='' 
                        try:
                            time.sleep(0.5)
                            output = ssm_boto_client.get_command_invocation(
                                CommandId=command_id,
                                InstanceId=instanceid)
                        except Exception as e:
                            print(e)
                        status = output['Status']
                        if(status in ['InProgress','Pending'] and attempt <=5):
                            time.sleep(0.5)
                        elif(status== 'Success'):
                            ssminstalled = 1
                            return ssminstalled
                        else:
                            break
                except Exception as e:
                    print('send_cmd_attempt - ',send_cmd_attempt)
                    print('Error check_ssm_status() -',e)
                    pass  
                if(send_cmd_attempt>5):
                    print('Send command execution failed. cmd - {}'.format(ssmcommand))
                    return ssminstalled
                else:
                    time.sleep(0.5)
                
        except Exception as e:
            return ssminstalled

    def exec_install_ssm(self,instanceId):
        #TODO: write code...
        ddb_inst_info_table_obj = self.ddb.Table(self.ddb_inst_info)
        response = ddb_inst_info_table_obj.get_item(Key={
                       'InstanceId': instanceId
                   })
        instance_data = response['Item']
        print(instance_data)

        instance_id = instance_data['InstanceId'].strip()
        osname = instance_data['os-name'].strip()            
        osarch = instance_data['os-arch'].strip()
        parametersetname = instance_data['ParameterSetName'].strip()
        
        return self.run_install_ssm(instance_id,osname,osarch,parametersetname)