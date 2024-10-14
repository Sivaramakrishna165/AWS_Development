'''
Implemented via [AWSPE - 6701]

# The lambda(sm1) recevies the trigger from the processor lambda
# Upon validating the instance os type the replication agent will be downloaded and installed in the Instance.
# Once the process completed successfully, a success status will be sent to stepfunction to invoke the next statemachine sm2.

sample event:

{
  "InstanceId": "",
  "OSName": "",
  "RecoveryRegion": "",
  "TaskToken":""
}


    Author : Arunkumar Chandrasekar
    CreationDate : 09 Jun 2023
    ModifiedDate : 09 Jun 2023

'''
import json
import boto3
from boto_helper import boto_helper
import time

boto_obj = boto_helper()

def lambda_handler(event, context):
    
    print("Event Received - ", event)
    
    instance_id = event['InstanceId']
    osname = event['OSName']
    recovery_region = event['RecoveryRegion']
    taskToken = event['TaskToken']
    
    error = {}
    error['InstanceId'] = instance_id
    error['RecoveryRegion'] = recovery_region      
    
    try:
    
        if 'windows' in osname.lower():
            print('Executing the windows Powershell script for {}'.format(osname))
            command = ['Invoke-WebRequest  https://aws-elastic-disaster-recovery-'+recovery_region+'.s3.'+recovery_region+'.amazonaws.com/latest/windows/AwsReplicationWindowsInstaller.exe -OutFile C:\\Windows\AwsReplicationWindowsInstaller.exe']
            document_name = 'AWS-RunPowerShellScript'
            response_command_id = boto_obj.execute_ssm_send_command(instance_id, document_name, command)
            
            status = boto_obj.get_invocation_status(instance_id, response_command_id)
            while (status in ['InProgress','Pending']):
                time.sleep(10)
                status = boto_obj.get_invocation_status(instance_id, response_command_id)
            
            print('Status -', status)
            if status.lower() == 'success':
                print('The replication agent downloaded successfully onto the instance {}'.format(instance_id))
                print('The replication agent installation has been started')
                
                command = ['C:\Windows\AwsReplicationWindowsInstaller.exe --region '+recovery_region+' --no-prompt']
                document_name = 'AWS-RunPowerShellScript'
                response_command_id = boto_obj.execute_ssm_send_command(instance_id, document_name, command)
                
                status = boto_obj.get_invocation_status(instance_id, response_command_id)
                while (status in ['InProgress','Pending']):
                    time.sleep(30)
                    status = boto_obj.get_invocation_status(instance_id, response_command_id)
                    print('Status -', status)
                
                if status.lower() == 'success':
                    
                    print('The replication agent has been installed successfully onto the instance {}'.format(instance_id))
                    payload_json = {'TaskToken':taskToken, 'InstanceId':instance_id, 'OSName':osname, 'RecoveryRegion':recovery_region, 'Message': 'Replication agent has been installed successfully onto the instance {}'.format(instance_id)}
                    boto_obj.handle_success(taskToken, payload_json)

                else:
                    print('ERROR occurred while installing the replication agent onto the instance {}'.format(instance_id))
                    error['Error'] = 'Error in replication agent installation'
                    error['Cause'] = 'Installation of replication agent onto the instance {} is failed'.format(instance_id)
                    boto_obj.handle_failure(taskToken, error, instance_id)                    
                                    
            else:
                print('ERROR while downloading the replication agent onto the instance {}'.format(instance_id))
                error['Error'] = 'Error occurred while downloading replication agent'
                error['Cause'] = 'Downloading the replication agent onto the instance {} is failed'.format(instance_id)
                boto_obj.handle_failure(taskToken, error, instance_id)

        elif 'Red Hat Enterprise Linux' in osname or 'Oracle' in osname:
            print('Executing the Linux Shell script for {}'.format(osname))
            command = [
                'sudo yum install elfutils-libelf-devel -y',
                'sudo curl -o aws-replication-installer-init https://aws-elastic-disaster-recovery-'+recovery_region+'.s3.'+recovery_region+'.amazonaws.com/latest/linux/aws-replication-installer-init'
                ]
            document_name = 'AWS-RunShellScript'
            response_command_id = boto_obj.execute_ssm_send_command(instance_id, document_name, command)
            
            status = boto_obj.get_invocation_status(instance_id, response_command_id)
            while (status in ['InProgress','Pending']):
                time.sleep(10)
                status = boto_obj.get_invocation_status(instance_id, response_command_id)
            
            print('Status -', status)
            if status.lower() == 'success':
                print('The elfutils-libelf-devel package is installed and replication agent downloaded successfully onto the instance {}'.format(instance_id))
                print('The replication agent installation has been started')
                
                command = ['sudo chmod +x aws-replication-installer-init; sudo ./aws-replication-installer-init --region ' +recovery_region+' --no-prompt']
                document_name = 'AWS-RunShellScript'
                response_command_id = boto_obj.execute_ssm_send_command(instance_id, document_name, command)
                
                status = boto_obj.get_invocation_status(instance_id, response_command_id)
                while (status in ['InProgress','Pending']):
                    time.sleep(30)
                    status = boto_obj.get_invocation_status(instance_id, response_command_id)
                    print('Status -', status)
                
                if status.lower() == 'success':
                    print('The replication agent has been installed successfully onto the instance {}'.format(instance_id))
                    payload_json = {'TaskToken':taskToken, 'InstanceId':instance_id, 'OSName':osname, 'RecoveryRegion':recovery_region, 'Message': 'Replication agent has been installed successfully onto the instance {}'.format(instance_id)}
                    boto_obj.handle_success(taskToken, payload_json)
                    
                else:
                    print('ERROR occurred while installing the replication agent onto the instance {}'.format(instance_id))
                    error['Error'] = 'Error in replication agent installation'
                    error['Cause'] = 'Installation of replication agent onto the instance {} is failed'.format(instance_id)
                    boto_obj.handle_failure(taskToken, error, instance_id)                    
                                    
            else:
                print('ERROR while downloading the replication agent onto the instance {}'.format(instance_id))
                error['Error'] = 'Error occurred while downloading replication agent'
                error['Cause'] = 'Downloading the replication agent onto the instance {} is failed'.format(instance_id)
                boto_obj.handle_failure(taskToken, error, instance_id)                
        
        else:
            print('Executing the Linux Shell script for {}'.format(osname))
            command = [
                'sudo curl -o aws-replication-installer-init https://aws-elastic-disaster-recovery-'+recovery_region+'.s3.'+recovery_region+'.amazonaws.com/latest/linux/aws-replication-installer-init'
                ]
            document_name = 'AWS-RunShellScript'
            response_command_id = boto_obj.execute_ssm_send_command(instance_id, document_name, command)
            
            status = boto_obj.get_invocation_status(instance_id, response_command_id)
            while (status in ['InProgress','Pending']):
                time.sleep(10)
                status = boto_obj.get_invocation_status(instance_id, response_command_id)
            
            print('Status -', status)
            if status.lower() == 'success':
                print('The replication agent downloaded successfully onto the instance {}'.format(instance_id))
                print('The replication agent installation has been started')
                
                command = ['sudo chmod +x aws-replication-installer-init; sudo ./aws-replication-installer-init --region ' +recovery_region+' --no-prompt']
                document_name = 'AWS-RunShellScript'
                response_command_id = boto_obj.execute_ssm_send_command(instance_id, document_name, command)
                
                status = boto_obj.get_invocation_status(instance_id, response_command_id)
                while (status in ['InProgress','Pending']):
                    time.sleep(30)
                    status = boto_obj.get_invocation_status(instance_id, response_command_id)
                    print('Status -', status)
                
                if status.lower() == 'success':
                    print('The replication agent has been installed successfully onto the instance {}'.format(instance_id))
                    payload_json = {'TaskToken':taskToken, 'InstanceId':instance_id, 'OSName':osname, 'RecoveryRegion':recovery_region, 'Message': 'Replication agent has been installed successfully onto the instance {}'.format(instance_id)}
                    boto_obj.handle_success(taskToken, payload_json)
                    
                else:
                    print('ERROR occurred while installing the replication agent onto the instance {}'.format(instance_id))
                    error['Error'] = 'Error in replication agent installation'
                    error['Cause'] = 'Installation of replication agent onto the instance {} is failed'.format(instance_id)
                    boto_obj.handle_failure(taskToken, error, instance_id)                    
                                    
            else:
                print('ERROR while downloading the replication agent onto the instance {}'.format(instance_id))
                error['Error'] = 'Error occurred while downloading replication agent'
                error['Cause'] = 'Downloading the replication agent onto the instance {} is failed'.format(instance_id)
                boto_obj.handle_failure(taskToken, error, instance_id)            
    
    except Exception as e:
        print('ERROR - ', str(e))
        error['Error'] = 'Error occurred while downloading/installing the replication agent'
        error['Cause'] = 'Download/Install the replication agent onto the instance {} is failed'.format(instance_id)
        boto_obj.handle_failure(taskToken, error, instance_id)
        raise