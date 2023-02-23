from django.core import mail
from django.test import override_settings
from django.utils.timezone import now
from freezegun import freeze_time
from mixer.backend.django import mixer

from crm.tasks import notify_inactive_customers
from elk.utils.testing import TestCase, create_customer, create_teacher
from lessons.models import OrdinaryLesson
from market.models import Subscription
from products.models import Product1


@override_settings(EMAIL_ASYNC=False)
class TestNotifyInactive(TestCase):
    fixtures = ('lessons', 'products')

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.customer = create_customer()
        cls.teacher = create_teacher()
        cls.lesson = OrdinaryLesson.get_default()
        cls.product = Product1.objects.get(pk=1)
        s = Subscription.objects.create(customer=cls.customer, product=cls.product)
        s.buy_date = cls.tzdatetime(2023, 2, 14)
        s.save()

    @freeze_time("2023-02-23 13:05")
    def test(self):
        entry = mixer.blend('timeline.Entry', teacher=self.teacher, lesson=self.lesson)
        entry.start = self.tzdatetime(2023, 2, 15, 11, 0)
        entry.end = self.tzdatetime(2023, 2, 15, 12, 0)
        entry.is_finished = True
        entry.save()
        mixer.blend('market.Class', customer=self.customer, timeline=entry)
        self.customer.subscriptions.update(is_fully_used=False)

        mail.outbox = []  # clear outbox
        notify_inactive_customers()

        self.assertEqual(1, len(mail.outbox))
        outbox = mail.outbox[0]
        self.assertIn(self.customer.email, outbox.to)
        self.assertEqual(
            outbox.subject,
            f"Hey, {self.customer.first_name}, you haven't been in for a long time."
        )
        self.customer.activity.refresh_from_db()
        self.assertEqual(self.customer.activity.last_notice_date, now().date())

    @freeze_time("2023-02-23 13:05")
    def test_if_active_customer(self):
        entry = mixer.blend('timeline.Entry', teacher=self.teacher, is_finished=True, lesson=self.lesson)
        entry.start = self.tzdatetime(2023, 2, 22, 11, 0)
        entry.end = self.tzdatetime(2023, 2, 22, 12, 0)
        entry.is_finished = True
        entry.save()
        mixer.blend('market.Class', customer=self.customer, timeline=entry)
        self.customer.subscriptions.update(is_fully_used=False)

        mail.outbox = []  # clear outbox
        notify_inactive_customers()

        self.assertEqual(0, len(mail.outbox))

    @freeze_time("2023-02-23 13:05")
    def test_if_customer_doesnt_have_active_subscriptions(self):
        entry = mixer.blend('timeline.Entry', teacher=self.teacher, lesson=self.lesson)
        entry.start = self.tzdatetime(2023, 2, 15, 11, 0)
        entry.end = self.tzdatetime(2023, 2, 15, 12, 0)
        entry.is_finished = True
        entry.save()
        mixer.blend('market.Class', customer=self.customer, timeline=entry)
        self.customer.subscriptions.update(is_fully_used=True)

        mail.outbox = []  # clear outbox
        notify_inactive_customers()

        self.assertEqual(0, len(mail.outbox))
