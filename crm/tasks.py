from datetime import timedelta

from django.db.models import Prefetch, Q
from django.utils.timezone import now

from elk.celery import app as celery
from mailer.owl import Owl


@celery.task(soft_time_limit=3600)
def notify_inactive_customers():
    """
    Notify subscribed customers about them inactive more than one week

    NOTE: when upgrade to django 2+ replace prefetches to Count(..., filter=Q())
    """
    from crm.models import Customer
    from market.models import Class, Subscription

    today = now()

    week_ago = today - timedelta(days=7)
    customers = Customer.objects.select_related('activity').prefetch_related(
        Prefetch(
            'classes',
            Class.objects.select_related('timeline').filter(timeline__end__gte=week_ago, timeline__is_finished=True),
            to_attr='past_7days_classes',
        ),
        Prefetch(
            'subscriptions',
            Subscription.objects.filter(is_fully_used=False).order_by('-buy_date'),
            to_attr='active_subscriptions',
        ),
    ).filter(
        Q(activity__last_notice_date__lte=week_ago) | Q(activity__last_notice_date__isnull=True),
    ).distinct()

    for customer in customers:
        if len(customer.active_subscriptions) == 0:
            continue
        if len(customer.past_7days_classes) > 0:
            continue

        if customer.active_subscriptions[0].buy_date > week_ago:
            continue

        customer.activity.last_notice_date = today.date()
        customer.activity.save()

        owl = Owl(
            template='mail/inactive_customer_notification.html',
            ctx={
                'c': customer,
            },
            to=[customer.user.email],
            timezone=customer.timezone,
        )
        owl.send()
