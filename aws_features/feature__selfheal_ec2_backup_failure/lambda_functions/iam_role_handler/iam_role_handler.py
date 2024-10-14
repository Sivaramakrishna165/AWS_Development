"""
This Lambda function is used to check the status of IAM role(default role or other role) attached to an instance or not, 
and IAM status as present or not_present.

This Lambda is a part of Selfheal ec2 backup failure.
In dxcms_sh_bf_sfn_diagnosis state machine(CheckIAMRole)
gets executed after checktags state.
In dxcms_sh_bf_sfn_resolution state machine(IAMRoleRemediation)
gets executed after checktagsRemediation state.

Input event of the lambda function is:
    {
        "instance_id":"<instance-id>",
        "Flag":"Fix"
    }

In Diagnosis state machine,
On successful check, next state - choicestatetostartinstance is called.
On FAILURE, next State CheckIAMRoleError and then NotifyForLambaFunctionFailure.
In Resolution state machine,
On successful check, next state - choicestatetostartinstance is called.
On FAILURE, next State IAMRoleRemediationError and then NotifyForLambaFunctionFailure
"""


import json
import boto3
import os
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

ec2_client = boto3.client('ec2',config=config)
iam_client = boto3.client('iam',config=config)

default_arn = os.environ['DefaultIAMRoleArn']

#input: instance_id
#it returns the current state of a particular instance.
def success_token(event,task_token):
    try:
        print("success_token() triggered.")
        sf = boto3.client('stepfunctions',config=config)
        sf_output = json.dumps(event)
        sf_response = sf.send_task_success(
            taskToken=task_token,
            output=str(sf_output)
        )
        print("success task token sent - ", sf_response)
        return sf_response
    except Exception as e:
        print("Error success_token() - ",e)
        print("not able to send task success token.")
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

def failure_token(taskToken, error, err_cause):
    try:
        print("failure_token() triggered.")
        if isinstance(err_cause, dict):
            cause = json.dumps(err_cause)
        else:
            cause = str(err_cause)
        sf = boto3.client('stepfunctions',config=config)
        sf_response = sf.send_task_failure(
            taskToken=taskToken,
            error = json.dumps(error),
            cause = cause
        )
        print('failure task token sent - ',sf_response)
    except Exception as e:
        print("Error failure_token() - ", e)
        print("not able to send failure task token")
        raise

def check_instance_state(instance_id):
    try:
        print("check_instance_state() triggered.")
        ec2 = boto3.resource('ec2',config=config)
        instance = ec2.Instance(instance_id)
        instance_state = instance.state['Name']
        return instance_state
    except Exception as e:
        print("Error check_instance_state() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

#calls check_key function, and checks if returned value is True or False
#If False, it only checks for Role Attached and Required Policies.
#If True, it fixes the issue based on values of Instance_IAM_Role and Required_Policies
def lambda_handler(event, context):
    global task_token, instance_id

    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id = event["instance_id"]
    try:
        Instance_State = check_instance_state(instance_id)
        instance_profile_arn = get_instance_profile_arn(instance_id)
        PolicyName = get_snapshot_policy()
        #print("Instance_State : ",Instance_State)
        req_policy = "Not_Attached"
        if check_key(event):
            Instance_IAM_Role = check_role(instance_id)
            #if no role is attached, calls attach_role function and attaches default role
            if (PolicyName == 'SnapshotPolicy'):
                if (Instance_IAM_Role == "No_Role"):
                    name=default_arn.split('/')[-1]
                    attach_role(name, instance_id)
                    Instance_IAM_Role = "Default_Role"
                    req_policy = "Attached"
                elif (Instance_IAM_Role == "Other_Role"):
                    attach_policies(PolicyName,instance_profile_arn)
                    req_policy = "Attached"
                else:
                    req_policy = "Attached"
                    pass

        #else, if check_key returns False
        #calls check_role for Instance_IAM_Role
        else:
            Instance_IAM_Role = check_role(instance_id)
            if (PolicyName == 'SnapshotPolicy'):
                if (Instance_IAM_Role == "Default_Role"):
                    req_policy = "Attached"
                else:
                    req_policy = "Not_Attached"

        if (req_policy == "Attached"):
            Instance_IAM_Status = "Present"
        else:
            Instance_IAM_Status = "Not_Present"

        #assigns all the values into event dictionary
        #returns event
        event["Instance_IAM_Status"] = Instance_IAM_Status
        event["Instance_IAM_Role"] = Instance_IAM_Role
        event["Instance_State"] = Instance_State
        return success_token(event,task_token)
    
    except Exception as e:
        print("Error lambda_handler() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

#input: instance_id, default_arn, instance_profile_arn
#this function checks for the IAM role attached to an instance.
def check_role(instance_id):
    try:
        print("check_role() triggered.")
        instance_profile_arn = get_instance_profile_arn(instance_id)

        #checks if there is a role attached to the instance or not
        if instance_profile_arn == None:
            Instance_IAM_Role = "No_Role"
        else:
            #if role is attached, then checks if it is default role or some other role
            if instance_profile_arn == default_arn:
                Instance_IAM_Role = "Default_Role"
            else:
                Instance_IAM_Role = "Other_Role"
        
        return Instance_IAM_Role

    except Exception as e:
        print("Error check_role() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())
    

#input: instance_id
#calls describe_iam_instance_profile_associations method of ec2 client from boto3 library.
#checks for IamInstanceProfileAssociations list from value stored in response.
def get_instance_profile_arn(instance_id):
    try:
        print("get_instance_profile_arn() triggered.")
        response = ec2_client.describe_iam_instance_profile_associations(
            Filters=[
                {'Name': 'instance-id', 'Values': [instance_id,]},
            ],
        )
        #if list is NOT empty, it gives back the arn of the role attached
        if response['IamInstanceProfileAssociations']:
            instance_profile_arn = (response['IamInstanceProfileAssociations'][0]['IamInstanceProfile']['Arn'])
        #if list is empty, this means there is no role attached so its returns None.
        else:
            instance_profile_arn = None

        return instance_profile_arn
    
    except Exception as e:
        print("Error get_instance_profile_arn() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

#input: name of role to attach, instance_id
#call associate_iam_instance_profile method of ec2 client to attach the role.
def attach_role(name, instance_id):
    try:
        print("attach_role() triggered.")
        response = ec2_client.associate_iam_instance_profile(
            IamInstanceProfile={
                'Name': name
            },
            InstanceId= instance_id
        )
    except Exception as e:
        print("Error attach_role() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

def get_snapshot_policy():
    try:
        print("get_snapshot_policy() triggered.")
        role_name=(default_arn.split('/'))[-1]
        response1 = iam_client.get_instance_profile(
            InstanceProfileName=role_name)
        role_instance=response1['InstanceProfile']['Roles'][0]['RoleName']

        inline_policies_attached = iam_client.list_role_policies(
            RoleName=role_instance
        )

        for policy in inline_policies_attached['PolicyNames']:
            if policy == 'SnapshotPolicy':
                flag = True
                break
            else:
                flag = False

        if (flag == True):
            return policy
        else:
            #print("Snapshot pol not present")
            return None

    except Exception as e:
        print("Error get_snapshot_policy() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

def attach_policies(policy_name, role_arn):
    try:
        print("attach_policies() triggered.")
        role_name=(role_arn.split('/'))[-1]
        response1 = iam_client.get_instance_profile(
            InstanceProfileName=role_name)
        role_instance=response1['InstanceProfile']['Roles'][0]['RoleName']
        
        default_role_name=(default_arn.split('/'))[-1]
        response2 = iam_client.get_instance_profile(
            InstanceProfileName=default_role_name)
        default_role_instance=response2['InstanceProfile']['Roles'][0]['RoleName']

        policy_document = iam_client.get_role_policy(
            RoleName=default_role_instance,
            PolicyName=policy_name
        )

        response3 = iam_client.put_role_policy(
            RoleName=role_instance,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document['PolicyDocument'])
        )

        #print("SnapshotPolicy attached")

    except Exception as e:
        print("Error attach_policies() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

#returns True iff there a key "Flag" in event dict, and the value of the key is "Fix"
#else returns False
def check_key(event):
    try:
        print("check_key() triggered.")
        if 'Flag' in event.keys():
            if event['Flag'] == 'Fix':
                return True
        
        return False
    except Exception as e:
        print("Error check_key() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())




event1 = {"instance_id" : "i-0908899829ed0feb3", 'Flag' : 'Fix'}
event2 = {"instance_id" : "i-0908899829ed0feb3"}

if __name__ == "__main__":
    lambda_handler(event1,"")