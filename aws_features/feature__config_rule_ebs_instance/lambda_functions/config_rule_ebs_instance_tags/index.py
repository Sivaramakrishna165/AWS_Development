#
# Driver for VolumeTagEvaluationLambda.py
#
from config_instances_tags import (InstanceTagEvaluation)


def lambda_handler(event, context):
    evaluation = InstanceTagEvaluation()
    return evaluation.handler_impl(event, context)
