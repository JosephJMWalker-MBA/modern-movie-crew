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


@transaction.atomic
def mark_notification_as_read(
    *,
    notif_id: int,
    user,
) -> Notification:
    notif = Notification.objects.select_for_update().get(pk=notif_id, membership__user=user)
    notif.is_read = True
    notif.save()
    return notif
