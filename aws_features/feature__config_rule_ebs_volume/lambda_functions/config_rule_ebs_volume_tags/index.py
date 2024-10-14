#
# Driver for VolumeTagEvaluationLambda.py
#
from config_volumes_tags import (VolumeTagEvaluation)


def lambda_handler(event, context):
    evaluation = VolumeTagEvaluation()
    return evaluation.handler_impl(event, context)
