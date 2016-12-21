from datetime import timedelta

from freezegun import freeze_time
from mixer.backend.django import mixer

from elk.utils.testing import TestCase, create_teacher
from lessons import models as lessons
from timeline.models import Entry as TimelineEntry


@freeze_time('2032-12-01 12:05')
class TestLessonsStartingSoon(TestCase):
    def setUp(self):
        self.host = create_teacher(works_24x7=True)

        self.lesson = mixer.blend(lessons.MasterClass, host=self.host, photo=mixer.RANDOM)

        self.entry = mixer.blend(
            TimelineEntry,
            teacher=self.host,
            lesson=self.lesson,
            start=self.tzdatetime(2032, 12, 1, 13, 00)
        )

    def test_starting_soon_for_lesson_type_none(self):
        starting_soon = TimelineEntry.objects.lessons_starting_soon(lesson_types=[lessons.PairedLesson.get_contenttype()])
        starting_soon = list(starting_soon)
        self.assertEqual(len(starting_soon), 0)

    def test_starting_soon_for_lesson_type_1(self):
        starting_soon = TimelineEntry.objects.lessons_starting_soon(lesson_types=[lessons.MasterClass.get_contenttype()])
        starting_soon = list(starting_soon)
        self.assertEqual(len(starting_soon), 1)

    def test_starting_soon_returns_lesosns(self):
        starting_soon = TimelineEntry.objects.lessons_starting_soon(lesson_types=[lessons.MasterClass.get_contenttype()])

        starting_soon = list(starting_soon)

        self.assertIsInstance(starting_soon[0], lessons.MasterClass)

    def test_starting_soon_returns_only_lessons_with_photos(self):
        self.lesson.photo = None
        self.lesson.save()

        starting_soon = TimelineEntry.objects.lessons_starting_soon(lesson_types=[lessons.PairedLesson.get_contenttype()])
        starting_soon = list(starting_soon)
        self.assertEqual(len(starting_soon), 0)

    @freeze_time('2032-12-05 12:00')
    def test_starting_soon_works_only_with_future_lessons(self):
        """
        Move 5 days forward and check that lesson should disappear
        """
        starting_soon = TimelineEntry.objects.lessons_starting_soon(lesson_types=[lessons.MasterClass.get_contenttype()])
        starting_soon = list(starting_soon)
        self.assertEqual(len(starting_soon), 0)

    def test_starting_soon_returns_only_free_entries(self):
        """
        Reduce the number of available students slots to 0 and check
        if lessons_starting_soon() does not return a lesson with that timeline
        entry.
        """
        self.lesson.slots = 0
        self.lesson.save()

        self.entry.slots = 0
        self.entry.save()

        starting_soon = TimelineEntry.objects.lessons_starting_soon(lesson_types=[lessons.MasterClass.get_contenttype()])
        starting_soon = list(starting_soon)
        self.assertEqual(len(starting_soon), 0)

    def test_starting_soon_returns_only_one_distinct_lesson(self):
        """
        Create 5 timeline entries and check if lessons_starting_soon() returns
        only one of them.
        """
        for i in range(0, 5):
            self.entry = mixer.blend(
                TimelineEntry,
                teacher=self.host,
                lesson=self.lesson,
                start=self.tzdatetime(2032, 12, 1, 13, 00) + timedelta(hours=i)
            )

        starting_soon = TimelineEntry.objects.lessons_starting_soon(lesson_types=[lessons.MasterClass.get_contenttype()])
        starting_soon = list(starting_soon)
        self.assertEqual(len(starting_soon), 1)  # should be only 1 lesson, because all lessons are equal
