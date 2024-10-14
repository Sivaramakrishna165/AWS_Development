'''
# Implemented via AWSPE-5779, AWSPE-6010 and AWSPE-6044
# Acceptance Criteria:

This Function is used to install Cloudwatch Agent and configure for instance while STEP 3 StateMachineInstanceTagging
if ApplyMonitoring is enabled then it will call apply_instance_monitoring.instance_monitoring to install Cloudwatch

'''
import boto3, time

class installExtraPack():
    def __init__(self,config, region='us-east-1'):
        self.ssm_client = boto3.client('ssm', config=config)
        self.config = config

    def exec_installExtraPack(self,instanceId,osname,osarch):
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
                    response = self.ssm_client.send_command(
                        InstanceIds=[instanceId],
                        DocumentName='AWS-ConfigureAWSPackage',
                        Parameters={'action': ['Install'],
                                    "installationType": ["Uninstall and reinstall"],
                                    'name': ['AwsVssComponents']}, )         
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
                    print('Error exec_installExtraPack() -',str(e))
                    StateDetail = str(e)
                    pass  
                if(send_cmd_attempt>3):
                    print('AWS Backup Agent installation for windows Failed becoz Send command execution failed. Please check the SSM agent status')
                    StateSuccessFail = 'FAIL'
                    return StateDetail,StateSuccessFail
                else:
                    time.sleep(30)
        except Exception as e:
            print('Error exec_installExtraPack() ',str(e))
            StateDetail = str(e)
            StateSuccessFail = 'FAIL'
        return StateDetail,StateSuccessFail