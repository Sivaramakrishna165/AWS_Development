"""
This Lambda function is used to check the status of IAM role(default role or other role) attached to an instance or not, 
and IAM status as present or not_present.

This Lambda is a part of Selfheal crowdstrike agent failure.
In dxcms_sh_cs_sfn_diagnosis state machine(CheckIAMRole)
gets executed after dxcms_sh_sfn_self_heal_master_sfn state machine.
In dxcms_sh_cs_sfn_resolution state machine(RemediateIAMRoleIssue)
gets executed after dxcms_sh_cs_sfn_diagnosis state machine.

Input event of the lambda function is:
    {
        "instance_id":"<instance-id>",
        "Flag":"Fix"
    }

In Diagnosis state machine,
On successful check, next state - FetchInstanceDetails is called.
On FAILURE, next State CheckIAMRoleError and then NotifyForLambaFunctionFailure.
In Resolution state machine,
On successful check, next state - FetchInstanceDetails is called.
On FAILURE, next State RemediateIAMRoleIssueError and then NotifyForLambaFunctionFailure
"""


import json
import boto3
import os
import traceback
from botocore.config import Config

config=Config(retries=dict(max_attempts=10,mode='standard'))

ec2_client = boto3.client('ec2',config=config)
iam_client = boto3.client('iam',config=config)
ssm_client = boto3.client('ssm',config=config)

default_arn = os.environ['DefaultIAMRoleArn']
policy_names_ssm_parameter = os.environ['policy_names']
# policy_names_ssm_parameter = "policy_names"

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

#input: instance_id
#it returns the current state of a particular instance.
def check_instance_state(instance_id):
    try:
        print("check_instance_state triggered.")
        ec2 = boto3.resource('ec2',config=config)
        instance = ec2.Instance(instance_id)
        instance_state = instance.state['Name']
        print("instance state is " + instance_state)
        return instance_state
    except Exception as e:
        print("Error check_instance_state() - ",e)
        print(f"Error while checking current state of instance {instance_id}.")
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

#calls check_key function, and checks if returned value is True or False
#If False, it only checks for Role Attached and Required Policies.
#If True, it fixes the issue based on values of instance_iam_role and Required_Policies
def lambda_handler(event, context):
    global task_token, instance_id
        
    print("input recieved to this script - " + str(event))
    task_token = event["token"]
    event = event["Payload"]
    instance_id = event["instance_id"]
    try:
        instance_state = check_instance_state(instance_id)
        instance_profile_arn = get_instance_profile_arn(instance_id)
        policies_to_attach = read_ssm_parameter_policy_names()
        required_policy = "Not_Attached"
        if check_key(event):
            instance_iam_role = check_role(instance_id)
            if (instance_iam_role == "no_role"):
                name=default_arn.split('/')[-1]
                attach_role(name, instance_id)
                instance_iam_role = "default_role"
                required_policy = "Attached"
            
            elif (instance_iam_role == "other_role"):
                all_policies_status = "Attached"
                
                if not policies_to_attach == []:
                    for policy in policies_to_attach:
                        if (policy["Policy_Type"] == "Customer inline"):
                            policy_name = check_inline_policy(policy["Policy_Name"])
                            if (policy_name == policy["Policy_Name"]):
                                policy_status = attach_inline_policy(policy_name, instance_profile_arn)
                                if (policy_status != "Policy_Attached"):
                                    all_policies_status = "Not_Attached"                            
                            else:
                                print("Default role does not have {} inline policy attached".format(policy["Policy_Name"]))
                                all_policies_status = "Not_Attached"
                        elif (policy["Policy_Type"] == "Customer managed"):
                            policy_status = attach_customer_managed_policy(policy["Policy_Name"], instance_profile_arn)
                            if (policy_status != "Policy_Attached"):
                                all_policies_status = "Not_Attached"
                        elif (policy["Policy_Type"] == "AWS managed"):
                            policy_status = attach_aws_managed_policy(policy["Policy_Name"], instance_profile_arn)
                            if (policy_status != "Policy_Attached"):
                                all_policies_status = "Not_Attached"
                        else:
                            print("Policy Type not matched. It can be either of the following: Customer inline/Customer managed/AWS managed")
                            all_policies_status = "Not_Attached"
                else:
                    print("no policies to attach. got empty list from ssm parameter.")
                
                if (all_policies_status == "Attached"):
                    required_policy = "Attached"
                else:
                    required_policy = "Not_Attached"

            else:
                required_policy = "Attached"
                pass

        #else, if check_key returns False
        #calls check_role for instance_iam_role
        else:
            instance_iam_role = check_role(instance_id)
            if (instance_iam_role == "default_role"):
                required_policy = "Attached"
            else:
                required_policy = "Not_Attached"

        if (required_policy == "Attached"):
            instance_iam_status = "present"
        else:
            instance_iam_status = "not_present"

        #assigns all the values into event dictionary
        #returns event
        event["instance_iam_status"] = instance_iam_status
        event["instance_iam_role"] = instance_iam_role
        event["instance_state"] = instance_state
        #print(event)
        # return event
        return success_token(event,task_token)
    
    except Exception as e:
        print("Error lambda_handler() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

#input: instance_id, default_arn, instance_profile_arn
#this function checks for the IAM role attached to an instance.
def check_role(instance_id):
    try:
        print("check_role triggered")
        instance_profile_arn = get_instance_profile_arn(instance_id)

        #checks if there is a role attached to the instance or not
        if instance_profile_arn == None:
            instance_iam_role = "no_role"
        else:
            #if role is attached, then checks if it is default role or some other role
            if instance_profile_arn == default_arn:
                instance_iam_role = "default_role"
            else:
                instance_iam_role = "other_role"
        
        print("attached role is " + instance_iam_role)
        return instance_iam_role

    except Exception as e:
        print("Error check_role() - ",e)
        print(f"Error while checking role of instance {instance_id}.")
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())
    

#input: instance_id
#calls describe_iam_instance_profile_associations method of ec2 client from boto3 library.
#checks for IamInstanceProfileAssociations list from value stored in response.
def get_instance_profile_arn(instance_id):
    try:
        print("get_instance_profile_arn triggered.")
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
            
        print("instance_profile_arn is " + str(instance_profile_arn))
        return instance_profile_arn
    
    except Exception as e:
        print("Error get_instance_profile_arn() - ",e)
        print(f"Unable to read iam role arn of instance {instance_id}")
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

#input: name of role to attach, instance_id
#call associate_iam_instance_profile method of ec2 client to attach the role.
def attach_role(name, instance_id):
    try:
        print("attach_role triggered.")
        response = ec2_client.associate_iam_instance_profile(
            IamInstanceProfile={
                'Name': name
            },
            InstanceId= instance_id
        )
        print("{} attached to the instance.".format(name))
    
    except Exception as e:
        print("Error attach_role() - ",e)
        print(f"Unable to attach role {name} to instance {instance_id}.")
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

def check_inline_policy(policy_name):
    try:
        print("check_inline_policy triggered.")
        role_name=(default_arn.split('/'))[-1]
        response1 = iam_client.get_instance_profile(
            InstanceProfileName=role_name)
        role_instance=response1['InstanceProfile']['Roles'][0]['RoleName']

        inline_policies_attached = iam_client.list_role_policies(
            RoleName=role_instance
        )

        for policy in inline_policies_attached['PolicyNames']:
            if policy == policy_name:
                flag = True
                break
            else:
                flag = False

        if (flag == True):
            print("inline policy to attach from default role = " + policy)
            return policy
        else:
            print("{} policy not present in default role".format(policy_name))
            return None

    except Exception as e:
        print("Error check_inline_policy() - ",e)
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

def attach_inline_policy(policy_name, role_arn):
    try:
        print("attach_inline_policy triggered")
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

        print("{} policy attached to {} role.".format(policy_name, role_name))

        return "Policy_Attached"

    except Exception as e:
        print("Error attach_inline_policy() - ",e)
        print(f"Unable to create inline policy {policy_name} to role {role_arn}")
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

def attach_aws_managed_policy(policy_name, role_arn):
    try:
        print("attach_aws_managed_policy triggered.")
        role_name = (role_arn.split('/'))[-1]
        response1 = iam_client.get_instance_profile(
            InstanceProfileName=role_name)
        role_instance=response1['InstanceProfile']['Roles'][0]['RoleName']
        policy_arn = "arn:aws:iam::aws:policy/" + policy_name

        response = iam_client.attach_role_policy(
            RoleName=role_instance,
            PolicyArn=policy_arn
        )
        print("{} policy attached to {} role.".format(policy_name, role_name))
        
        return "Policy_Attached"
    
    except Exception as e:
        print("Error attach_aws_managed_policy() - ",e)
        print(f"Unable to attach aws managed policy {policy_name} to role {role_arn}")
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

def attach_customer_managed_policy(policy_name, role_arn):
    try:
        print("attach_customer_managed_policy triggered.")
        AccountName = boto3.client('iam',config=config).list_account_aliases()['AccountAliases'][0]

        role_name = (role_arn.split('/'))[-1]
        response1 = iam_client.get_instance_profile(
            InstanceProfileName=role_name)
        role_instance=response1['InstanceProfile']['Roles'][0]['RoleName']
        
        policy_arn = "arn:aws:iam::" + AccountName + ":policy/" + policy_name

        response = iam_client.attach_role_policy(
            RoleName=role_instance,
            PolicyArn=policy_arn
        )
        print("{} policy attached to {} role.".format(policy_name, role_name))
        
        return "Policy_Attached"
    
    except Exception as e:
        print("Error attach_customer_managed_policy() - ",e)
        print(f"Unable to attach customer managed policy {policy_name} to role {role_arn}")
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())


def read_ssm_parameter_policy_names():
    try:
        print("read_ssm_parameter_policy_names triggered.")
        response = ssm_client.get_parameter(
            Name = policy_names_ssm_parameter
        )
        policies = json.loads(response['Parameter']['Value'])

        print("Policies to attach = " + str(policies))
        return policies
    
    except Exception as e:
        print("Error read_ssm_parameter_policy_names() - ",e)
        print(f"unable to read value from ssm paramter {policy_names_ssm_parameter}.")
        input = {"error" : str(e), "resource_id" : instance_id, "resource_type" : "EC2 Instance"}
        failure_token(task_token, input, traceback.format_exc())

#returns True iff there a key "Flag" in event dict, and the value of the key is "Fix"
#else returns False
def check_key(event):
    try:
        print("check_key triggered.")
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