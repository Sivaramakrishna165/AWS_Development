'''
# Implemented via AWSPE-5779, AWSPE-6010 and AWSPE-6044
# Acceptance Criteria:

This Function is used to install Cloudwatch Agent and configure for instance while STEP 3 StateMachineInstanceTagging
if ApplyMonitoring is enabled then it will call apply_instance_monitoring.instance_monitoring to install Cloudwatch

'''
import boto3, time
from botocore.config import Config
from boto3.dynamodb.conditions import Key
import awscli_command_os_type

class installawscli():
    def __init__(self,config, region='us-east-1'):
        self.ssm_client = boto3.client('ssm', config=config)
        self.config = config
        x86_64_arch_key = "x86_64"
        arm_arch_key = "Arm"
        x86_64_arch = "x86_64"
        arm_arch = "aarch64"
        self.region = region
        self.awscli_command_dict = { "AMAZON-LINUX2_{}".format(x86_64_arch_key) : awscli_command_os_type.amazonlinux_awscli_command.format(x86_64_arch),
                                     "AMAZON-LINUX2_{}".format(arm_arch_key) : awscli_command_os_type.amazonlinux_awscli_command.format(arm_arch),
                                     "AMAZON-LINUX_{}".format(x86_64_arch_key) : awscli_command_os_type.amazonlinux_awscli_command.format(x86_64_arch),
                                     "AMAZON-LINUX_{}".format(arm_arch_key) : awscli_command_os_type.amazonlinux_awscli_command.format(arm_arch),
                                     "RHEL_{}".format(x86_64_arch_key) : awscli_command_os_type.rhel_awscli_command.format(x86_64_arch),
                                     "RHEL_{}".format(arm_arch_key) : awscli_command_os_type.rhel_awscli_command.format(arm_arch),
                                     "UBUNTU_{}".format(x86_64_arch_key) : awscli_command_os_type.ubuntu_awscli_command.format(x86_64_arch),
                                     "UBUNTU_{}".format(arm_arch_key) : awscli_command_os_type.ubuntu_awscli_command.format(arm_arch),
                                     "SUSE_{}".format(x86_64_arch_key): awscli_command_os_type.suse_awscli_command.format(x86_64_arch),
                                     "SUSE_{}".format(arm_arch_key): awscli_command_os_type.suse_awscli_command.format(arm_arch),
                                     "ORACLE_{}".format(x86_64_arch_key): awscli_command_os_type.oracle_awscli_command.format(x86_64_arch),
                                     "ORACLE_{}".format(arm_arch_key): awscli_command_os_type.oracle_awscli_command.format(arm_arch),
                                     "WINDOWS_{}".format(x86_64_arch_key) : awscli_command_os_type.windows_awscli_command.format(x86_64_arch)
                                }

    def exec_installawscli(self,instanceId,osname,osarch):
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
                    os_info = osname + '_' + osarch
                    awscli_command = self.awscli_command_dict[os_info]
                    if osname == "WINDOWS":
                        DocumentName = "AWS-RunPowerShellScript"
                    else:
                        DocumentName = "AWS-RunShellScript"
                    response = self.ssm_client.send_command(
                        InstanceIds=[instanceId],
                        DocumentName=DocumentName,
                        Parameters={'commands': [awscli_command]}, )           
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
                        if(status in ['InProgress','Pending'] and attempt <=5):
                            time.sleep(0.5)
                        elif(status== 'Success'):
                            StateSuccessFail = 'SUCCESS'
                            return StateDetail,StateSuccessFail
                        else:
                            break
                except Exception as e:
                    print('send_cmd_attempt - ',send_cmd_attempt)
                    print('Error exec_installawscli() -',str(e))
                    StateDetail = str(e)
                    pass  
                if(send_cmd_attempt>3):
                    print('AWS CLI Agent installation  Failed becoz Send command execution failed. Please check the SSM agent status')
                    StateSuccessFail = 'FAIL'
                    return StateDetail,StateSuccessFail
                else:
                    time.sleep(30)
        except Exception as e:
            print('Error exec_installawscli() ',str(e))
            StateDetail = str(e)
            StateSuccessFail = 'FAIL'
        return StateDetail,StateSuccessFail