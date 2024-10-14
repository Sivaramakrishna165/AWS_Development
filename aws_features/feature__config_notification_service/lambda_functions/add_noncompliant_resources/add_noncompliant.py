#
# Add non-compliant resources discovered in AWS Config
# to DynamoDB table.
#
# Trigger Type: Step Function State [AddNonCompliantResources]
# Scope: Non-Compliant Resources in AWS Config
# Accepted Parameter: None
#

from __future__ import print_function
import boto3


class GetParameterException(Exception):
    pass


class GetTableException(Exception):
    pass


class ConfigStatusExecutionException(Exception):
    pass


class ComplianceDetailsException(Exception):
    pass


class PutItemException(Exception):
    pass


class AddNonCompliantResources:
    def __init__(self):
        session = boto3.Session()
        self.config = session.client('config')
        self.dynamodb = session.resource('dynamodb')
        self.ssm = session.client('ssm')
        self.offerings_config_rules_prefix = 'FeatureConfigRule'

    def add_items(self, table, config_rule, result):
        rule_name = config_rule['ConfigRuleName']
        resource_id = (result['EvaluationResultIdentifier']
                       ['EvaluationResultQualifier']
                       ['ResourceId'])
        resource_type = (result['EvaluationResultIdentifier']
                         ['EvaluationResultQualifier']
                         ['ResourceType'])
        rule_arn = config_rule['ConfigRuleArn']
        try:
            table.put_item(
                Item={
                     'ConfigRuleName': rule_name,
                     'ResourceId': resource_id,
                     'ResourceType': resource_type,
                     'ConfigRuleArn': rule_arn,
                     'Notification': 'false'
                },
                ConditionExpression='((ResourceId = :v_Id) AND \
                                     (ConfigRuleName <> :v_RuleName)) OR \
                                     attribute_not_exists(ResourceId)',
                ExpressionAttributeValues={
                                          ":v_Id": resource_id,
                                          ":v_RuleName": rule_name
                }
            )
            print("Added Non-Compliant Resource: " + str(resource_id))
        except boto3.exceptions.botocore.client.ClientError as e:
            if (e.response['Error']['Code'] ==
               'ConditionalCheckFailedException'):
                """
                Non-compliant resource already reported in
                DynamoDB Table, so no need to re-add it.
                """
                pass
            else:
                """
                An unexpected error occurred, so return the error
                """
                print("Error adding item: %s" % e)
                raise PutItemException("Error adding item: %s" % e)

    def handler_impl(self, event, context):
        print('Function Name: ' + context.function_name)
        print('Function Version: ' + context.function_version)
        try:
            table_param = self.ssm.get_parameter(
                              Name='/DXC/ConfigService/DynamoDBTableName'
                          )
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error accessing SSM parameter: %s" % e)
            raise GetParameterException("Error: %s" % e)
        try:
            table = self.dynamodb.Table(table_param['Parameter']['Value'])
        except boto3.exceptions.botocore.client.ClientError as e:
            print("Error accessing DynamoDB table: %s" % e)
            raise GetTableException("Error: %s" % e)
        
        extra_args = {}
        while True:
            try:
                results = self.config.describe_config_rule_evaluation_status(**extra_args)
            except boto3.exceptions.botocore.client.ClientError as e:
                print("Error obtaining Config evaluations: %s" % e)
                raise ConfigStatusExecutionException("Error: %s" % e)
            for config_rule in results['ConfigRulesEvaluationStatus']:
                if(self.offerings_config_rules_prefix not in config_rule['ConfigRuleName']):
                    continue
                print('Config Rule - ',config_rule['ConfigRuleName'])
                try:
                    non_comp = self.config.get_compliance_details_by_config_rule(
                                ConfigRuleName=config_rule['ConfigRuleName'],
                                ComplianceTypes=['NON_COMPLIANT']
                            )
                except boto3.exceptions.botocore.client.ClientError as e:
                    print("Error obtaining Config rule evaluations: %s" % e)
                    raise ComplianceDetailsException("Error: %s" % e)
                for result in non_comp['EvaluationResults']:
                    self.add_items(table, config_rule, result)

            if 'NextToken' in results:
                extra_args['NextToken'] = results['NextToken']
            else:
                break
