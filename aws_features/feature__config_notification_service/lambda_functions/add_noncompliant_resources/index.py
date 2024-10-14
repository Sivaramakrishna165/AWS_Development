#
# Driver for add_noncompliant.py
#

from add_noncompliant import AddNonCompliantResources


def lambda_handler(event, context):
    add_noncompliant = AddNonCompliantResources()
    return add_noncompliant.handler_impl(event, context)
