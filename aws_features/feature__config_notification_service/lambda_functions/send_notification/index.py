#
# Driver for send_sns.py
#

from send_sns import SendNotification


def lambda_handler(event, context):
    notification = SendNotification()
    return notification.handler_impl(event, context)
