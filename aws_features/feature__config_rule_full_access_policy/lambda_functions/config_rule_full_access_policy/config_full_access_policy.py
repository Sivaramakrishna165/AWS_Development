#
#  Check for any Full access policies are attached:
#
# Trigger Type: Change Triggered
# Scope: AWS::IAM::Role
#

from datetime import tzinfo, datetime, timedelta
import json,os
import boto3
import time
import random
import dateutil.parser

from botocore.config import Config


ZERO = timedelta(0)


class UTC(tzinfo):
    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO


utc = UTC()


class FullAccessPolicyEvaluation:
    
    def __init__(self):
        
        config=Config(retries=dict(max_attempts=10,mode='standard'))
        self.config = boto3.client('config',config=config)
        self.iam_client=boto3.client('iam',config=config)
        self.ssm_client = boto3.client('ssm', config=config)

        self.risky_policies_param = os.environ['RISKY_POLICIES']

    def is_applicable(self, config_item, event):
        status = config_item['configurationItemStatus']
        event_left_scope = event['eventLeftScope']
        test = ((status in ['OK', 'ResourceDiscovered']) and
                event_left_scope is False)
        return test


    def is_ec2_role(self,role_name):
        assume_role_policy_document = self.get_assume_role_policy_document(role_name)
        for statement in assume_role_policy_document['Statement']:
            if 'Service' in statement['Principal'].keys():
                service_list = statement['Principal']['Service']
                ec2_role = 'ec2.amazonaws.com' in service_list
                if ec2_role:
                    return True
        return False

    def get_assume_role_policy_document(self,role_name):
        role = self.iam_client.get_role(RoleName=role_name)
        assume_role_policy_document = role["Role"]["AssumeRolePolicyDocument"]
        return assume_role_policy_document

    def get_attached_risky_policies(self,role_name):
        managed_policy_arn_and_name = self.get_all_role_managed_policy_arn_and_name(role_name)
        attached_risky_policies = []

        RISKY_POLICIES =  self.ssm_client.get_parameter(Name = self.risky_policies_param,
                                            WithDecryption=True)['Parameter']['Value']

        for policy_arn, policy_name in managed_policy_arn_and_name.items():
            if policy_name in RISKY_POLICIES:
                print(f"Found a high risk policy {policy_name} for role {role_name}")
                attached_risky_policies.append(policy_name)
        return attached_risky_policies

    def get_all_role_managed_policy_arn_and_name(self,role_name):
        all_role_managed_policies_arn_and_name = {}
        list_policy_arn = self.iam_client.list_attached_role_policies(RoleName=role_name, MaxItems=1000)
        while True:
            for policy_dict in list_policy_arn['AttachedPolicies']:
                all_role_managed_policies_arn_and_name[policy_dict['PolicyArn']] = policy_dict['PolicyName']
            if 'Marker' in list_policy_arn:
                list_policy_arn = iam_client.list_attached_role_policies(RoleName=role_name, MaxItems=1000,
                                                                         Marker=list_policy_arn['Marker'])
            else:
                break
        return all_role_managed_policies_arn_and_name

    def check_full_access_policy(self, configuration_item):
        try:
            role_name = configuration_item['configuration']['roleName']
            arn = configuration_item['configuration']['arn']
            resource_id = configuration_item['resourceId']
            print(f"Evaluating compliance for role:{role_name}")

            evaluations = []

            if not self.is_ec2_role(role_name):
                print(f"Role {role_name} is not an ec2 service role, skipping the check for high risk policies"
                      f" --> COMPLIANT")
                #return "COMPLIANT"
                compliance_value = 'COMPLIANT'

            else:
                print(f"Role {role_name} is an ec2 service role")

                attached_risky_policies = self.get_attached_risky_policies(role_name)
                print(f"Got attached high risk policies for role {role_name}: {attached_risky_policies}")

                if len(attached_risky_policies) == 0:
                    print(f"Role {role_name} has none of the listed high risk policies attached --> COMPLIANT")
                    #return "COMPLIANT"
                    compliance_value = 'COMPLIANT'

                else:
                    attached_risky_policies_str = ", ".join(attached_risky_policies)
                    annotation = f'Role {role_name} has the following high risk managed policy(policies) attached:' \
                                f' {attached_risky_policies_str}'
                    compliance_value = 'NON_COMPLIANT'

            evaluations.append(
                        {
                            'Annotation': 'Evaluation of IAM Role: ' + role_name,
                            'ComplianceResourceType': 'AWS::IAM::Role',
                            'ComplianceResourceId': resource_id,
                            'ComplianceType': compliance_value,
                            'OrderingTimestamp': datetime.now(utc)
                        }
                    )

            return evaluations

        except Exception as e:
            print('error in check_full_access_policy():',e)
            raise

    def evaluate_compliance(self, config_item):
        if config_item['resourceType'] != 'AWS::IAM::Role' or config_item['configurationItemStatus'] in ['ResourceDeletedNotRecorded', 'ResourceNotRecorded', 'ResourceDeleted']:
            return 'NOT_APPLICABLE'

        #evaluations = self.check_instance_tags(config_item, rule_parameters)
        evaluations = self.check_full_access_policy(config_item)

        return evaluations

    def process_evaluations(self, evaluations):
        eval_max = 99
        for i in range(0, len(evaluations), eval_max):
            yield evaluations[i:i+eval_max]

    def handler_impl(self, event, context):
        invoking_event = json.loads(event['invokingEvent'])

        evaluations = None
        if self.is_applicable(invoking_event['configurationItem'], event):
            evaluations = self.evaluate_compliance(
                invoking_event['configurationItem']
                )

        if not evaluations:
            print('No Evaluations Present')
        else:
            timeout = int(time.time()) + 3*int(1)
            chunked_evaluations = self.process_evaluations(evaluations)
            for evals in chunked_evaluations:
                response = self.config.put_evaluations(
                    Evaluations=evals,
                    ResultToken=event['resultToken'])

                if 'FailedEvaluations' in response and response['FailedEvaluations']:
                    error_message = ("Failed to report all evaluations "
                                     "successfully to the AWSConfig service. "
                                     "Failed: " + str(response['FailedEvaluations']))
                    raise Exception(error_message)

                sleep_time = min(int(timeout), random.uniform(2, 2*3))
                print("Sleep " + str(sleep_time) + " seconds before next request..")
                time.sleep(sleep_time)