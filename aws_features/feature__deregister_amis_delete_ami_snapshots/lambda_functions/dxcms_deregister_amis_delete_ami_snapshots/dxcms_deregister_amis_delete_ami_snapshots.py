'''
 The FeatureDeregisterHardened AMIs will help in deregistering the AMI automatically based on DeleteOn tag value
 And deletes the AMI snapshots based on the DeleteOn Tag value
 The lambda function is invoked by Event Bridge rule - "AWSMS-DeregisterAmisDeleteSnapshots"
 For initating deregister Hardened amis - {"RequestType": "DeregisterAmisDeleteSnapshots"}
'''

import json, os
from boto_helper import boto_helper
from datetime import date

today = date.today()
ssm_ami_snap_desc = os.environ['ssmDeleteAmiSnapshotDescription']

def lambda_handler(event, context):
    try:
        print('Event received- ',event)
        region = context.invoked_function_arn.split(':')[3]
        boto_helper_obj = boto_helper(region)
        
        if ('RequestType' not in event):
            raise Exception('Not a event, expected events are {"RequestType": "DeregisterAmisDeleteSnapshots"}')
        
        if('DeregisterAmisDeleteSnapshots' in event['RequestType']):
            ami_snap_desc = boto_helper_obj.get_ssm_param_val(ssm_ami_snap_desc).split(',')
            amis_list = boto_helper_obj.describe_amis()
            ami_snapshot_list = boto_helper_obj.describe_ami_snapshots(ami_snap_desc)
            
            print('*'*5, 'Describing AMIs and AMI Snapshots where DeleteOn is older than or same as {}'.format(today), '*'*5)
            print('AMI list - {}'.format(amis_list))
            print('AMI Snapshots - {}'.format(ami_snapshot_list))
            
            if(amis_list):
                print('Initiating De-Registering of AMIs:')
                for image in amis_list:
                    boto_helper_obj.de_register_ami(image)

            if(ami_snapshot_list):
                print('Initiating deletion if AMI Snapshots:')
                for snap in ami_snapshot_list:
                    boto_helper_obj.delete_snapshot(snap)

        return "Executed Seccessfully"
    except Exception as e:
        print('Lambda execution failed ',e)
