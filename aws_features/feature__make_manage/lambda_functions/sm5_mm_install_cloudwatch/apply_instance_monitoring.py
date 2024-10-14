'''
# Implemented via AWSPE-5779, AWSPE-6010 and AWSPE-6044
# Acceptance Criteria:

This Function is used to install Cloudwatch Agent and configure for instance while STEP 5 StateMachineInstallCloudwatch
if ApplyMonitoring is enabled then it will call apply_instance_monitoring.instance_monitoring to install Cloudwatch

# Statemachine Lambda splitup implemented via [AWSPE-6392]
'''
import boto3, time
from botocore.config import Config
from boto3.dynamodb.conditions import Key
import cloudwatch_command_os_type

class instance_monitoring():
    def __init__(self,config, region='us-east-1'):
        self.ssm_client = boto3.client('ssm', config=config)
        self.config = config
        x86_64_arch_key = "x86_64"
        arm_arch_key = "Arm"
        x86_64_arch = "amd64"
        arm_arch = "arm64"
        self.region = region
        self.cloudwatch_command_dict = { "AMAZON-LINUX2_{}".format(x86_64_arch_key) : [cmd.format(r=self.region,a=x86_64_arch) for cmd in cloudwatch_command_os_type.amazonlinux2_cloudwatch_command],
                                          "AMAZON-LINUX2_{}".format(arm_arch_key) : [cmd.format(r=self.region,a=arm_arch) for cmd in cloudwatch_command_os_type.amazonlinux2_cloudwatch_command],
                                          "AMAZON-LINUX_{}".format(x86_64_arch_key) : [cmd.format(r=self.region,a=x86_64_arch) for cmd in cloudwatch_command_os_type.amazonlinux2_cloudwatch_command],
                                          "AMAZON-LINUX_{}".format(arm_arch_key) : [cmd.format(r=self.region,a=arm_arch) for cmd in cloudwatch_command_os_type.amazonlinux2_cloudwatch_command],
                                          "RHEL_{}".format(x86_64_arch_key) : [cmd.format(r=self.region,a=x86_64_arch) for cmd in cloudwatch_command_os_type.rhel_cloudwatch_command],
                                          "RHEL_{}".format(arm_arch_key) : [cmd.format(r=self.region,a=arm_arch) for cmd in cloudwatch_command_os_type.rhel_cloudwatch_command],
                                          "UBUNTU_{}".format(x86_64_arch_key) : [cmd.format(r=self.region,a=x86_64_arch) for cmd in cloudwatch_command_os_type.ubuntu_cloudwatch_command],
                                          "UBUNTU_{}".format(arm_arch_key) : [cmd.format(r=self.region,a=arm_arch) for cmd in cloudwatch_command_os_type.ubuntu_cloudwatch_command],
                                          "SUSE_{}".format(x86_64_arch_key): [cmd.format(r=self.region,a=x86_64_arch) for cmd in cloudwatch_command_os_type.suse_cloudwatch_command],
                                          "SUSE_{}".format(arm_arch_key): [cmd.format(r=self.region,a=arm_arch) for cmd in cloudwatch_command_os_type.suse_cloudwatch_command],
                                          "ORACLE_{}".format(x86_64_arch_key): [cmd.format(r=self.region,a=x86_64_arch) for cmd in cloudwatch_command_os_type.oracle_cloudwatch_command],
                                          "ORACLE_{}".format(arm_arch_key): [cmd.format(r=self.region,a=arm_arch) for cmd in cloudwatch_command_os_type.oracle_cloudwatch_command],
                                          "WINDOWS_{}_cmd1".format(x86_64_arch_key) : [cmd.format(r=self.region,a=x86_64_arch) for cmd in cloudwatch_command_os_type.windows_cloudwatch_command1],
                                          "WINDOWS_{}_cmd2".format(x86_64_arch_key) : [cmd.format(r=self.region,a=x86_64_arch) for cmd in cloudwatch_command_os_type.windows_cloudwatch_command2]
                                        }

    def exec_instance_monitoring(self,instanceId,osname,osarch, optional_extend=''):
        """
        """
        StateDetail = ''
        StateSuccessFail = ''
        waiter = self.ssm_client.get_waiter('command_executed')
        try:
            send_cmd_attempt = 0
            while True:
                send_cmd_attempt += 1
                try:
                    os_info = osname + '_' + osarch + optional_extend
                    cloudwatch_command = self.cloudwatch_command_dict[os_info]
                    if osname == "WINDOWS":
                        DocumentName = "AWS-RunPowerShellScript"
                    else:
                        DocumentName = "AWS-RunShellScript"
                        
                    if(isinstance(cloudwatch_command,str)):
                        cmd = {'commands': [cloudwatch_command]}
                        
                    else: cmd = {'commands': cloudwatch_command}
                    response = self.ssm_client.send_command(
                        InstanceIds=[instanceId],
                        DocumentName=DocumentName,
                        Parameters = cmd)
                    command_id = response['Command']['CommandId']
                    print('response:',response)
                    print('command_id:',command_id)
                    waiter.wait(
                        CommandId=command_id,
                        InstanceId=instanceId,
                        #PluginName='string',
                        WaiterConfig={
                            'Delay': 10,
                            'MaxAttempts': 10
                        }
                    )
                    attempt = 0
                    while True:
                        attempt += 1
                        output ='' 
                        try:
                            time.sleep(0.5)
                            output = self.ssm_client.get_command_invocation(
                                CommandId=command_id,
                                InstanceId=instanceId)
                        except Exception as e:
                            print(e)
                        print('output:',output)
                        status = output['Status']
                        print(status)
                        if(status in ['InProgress','Pending'] and attempt <=10):
                            time.sleep(0.5)
                        elif(status== 'Success'):
                            if('verify that the path is correct and try again' in output['StandardOutputContent']):
                                break
                            StateSuccessFail = 'SUCCESS'
                            return StateDetail,StateSuccessFail
                        else:
                            break
                except Exception as e:
                    print('send_cmd_attempt - ',send_cmd_attempt)
                    print('Error exec_instance_monitoring() -',str(e))
                    StateDetail = str(e)
                    pass  
                if(send_cmd_attempt>3):
                    print('Cloudwatch Agent installation  Failed becoz Send command execution failed. Please check the SSM agent status')
                    StateSuccessFail = 'FAIL'
                    return StateDetail,StateSuccessFail
                else:
                    time.sleep(30)
        except Exception as e:
            print('Error exec_instance_monitoring() ',str(e))
            StateDetail = str(e)
            StateSuccessFail = 'FAIL'
        return StateDetail,StateSuccessFail