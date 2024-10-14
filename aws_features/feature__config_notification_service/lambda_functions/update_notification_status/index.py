#
# Driver for update_notification.py
#

from update_notification import UpdateNotificationStatus


def lambda_handler(event, context):
    notification = UpdateNotificationStatus()
    return notification.handler_impl(event, context)
