from django.db import transaction
from apps.core.models import Notification


@transaction.atomic
def create_notification(
    *,
    membership,
    title: str,
    message: str,
    link_url: str = "",
) -> Notification:
    return Notification.objects.create(
        membership=membership,
        title=title,
        message=message,
        link_url=link_url,
    )
