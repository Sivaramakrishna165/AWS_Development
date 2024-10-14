#
# Driver for remove_resources.py
#

from remove_resources import RemoveCompliantResources


def lambda_handler(event, context):
    remove_compliant = RemoveCompliantResources()
    return remove_compliant.handler_impl(event, context)
