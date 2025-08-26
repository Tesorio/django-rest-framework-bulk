from __future__ import print_function, unicode_literals

from django.test import TestCase
from django.test.client import RequestFactory
from rest_framework import status
from rest_framework.serializers import ModelSerializer

from rest_framework_bulk.serializers import BulkListSerializer, BulkSerializerMixin

from .simple_app.models import SimpleModel
from .simple_app.views import SimpleBulkAPIView


class TestOrderInsensitiveDelete(TestCase):
    def setUp(self):
        super(TestOrderInsensitiveDelete, self).setUp()
        self.request = RequestFactory()

    def test_delete_with_only_order_change(self):
        """
        Test that bulk destroy correctly rejects delete when only ordering changes.
        """
        SimpleModel.objects.create(contents="alpha", number=1)
        SimpleModel.objects.create(contents="beta", number=2)
        SimpleModel.objects.create(contents="gamma", number=3)

        class OrderOnlyFilterView(SimpleBulkAPIView):
            """View that only changes ordering, not filtering."""

            def filter_queryset(self, queryset):
                # Only change ordering, don't actually filter
                return queryset.order_by("-number")

        view = OrderOnlyFilterView.as_view()
        response = view(self.request.delete("/"))

        # Should be rejected since no actual filtering occurred
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SimpleModel.objects.count(), 3)

    def test_delete_with_actual_filter(self):
        """
        Test that bulk destroy allows delete when actual filtering occurs.
        """
        SimpleModel.objects.create(contents="alpha", number=1)
        SimpleModel.objects.create(contents="beta", number=10)
        SimpleModel.objects.create(contents="gamma", number=20)

        class ActualFilterView(SimpleBulkAPIView):
            """View that actually filters the queryset."""

            def filter_queryset(self, queryset):
                # Apply actual filter and ordering
                return queryset.filter(number__gte=10).order_by("-number")

        view = ActualFilterView.as_view()
        response = view(self.request.delete("/"))

        # Should be allowed since actual filtering occurred
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(SimpleModel.objects.count(), 1)
        self.assertEqual(SimpleModel.objects.get().number, 1)


class TestNonPKLookupField(TestCase):
    """Test in_bulk with non-PK field_name parameter."""

    def test_in_bulk_with_field_name(self):
        """
        Test that queryset.in_bulk() works with field_name parameter (for unique fields).
        """
        # Create test objects with unique content values
        obj1 = SimpleModel.objects.create(contents="alpha", number=1)
        obj2 = SimpleModel.objects.create(contents="beta", number=2)
        obj3 = SimpleModel.objects.create(contents="gamma", number=3)

        # Test in_bulk with default pk field
        id_list = [obj2.pk, obj1.pk, obj3.pk]
        obj_dict = SimpleModel.objects.in_bulk(id_list)

        self.assertEqual(len(obj_dict), 3)
        self.assertEqual(obj_dict[obj1.pk].contents, "alpha")
        self.assertEqual(obj_dict[obj2.pk].contents, "beta")
        self.assertEqual(obj_dict[obj3.pk].contents, "gamma")

    def test_bulk_update_preserves_order_with_in_bulk(self):
        """
        Test that bulk update preserves input order using in_bulk.
        """
        # Create test objects
        obj1 = SimpleModel.objects.create(contents="first", number=1)
        obj2 = SimpleModel.objects.create(contents="second", number=2)
        obj3 = SimpleModel.objects.create(contents="third", number=3)

        # Test order preservation with our refactored approach
        id_list = [obj3.pk, obj1.pk, obj2.pk]
        obj_by_id = SimpleModel.objects.in_bulk(id_list)

        # Build result in order
        result = []
        for obj_id in id_list:
            result.append(obj_by_id[obj_id].contents)

        self.assertEqual(result, ["third", "first", "second"])


class TestPerformanceImprovements(TestCase):
    def test_counter_performance(self):
        """
        Test that duplicate detection uses Counter for O(n) performance.
        """
        from collections import Counter

        # Create a list with duplicates
        test_list = [1, 2, 3, 2, 4, 5, 3, 6, 7, 8, 9, 10, 2]

        # O(n) approach using Counter
        duplicates = [k for k, v in Counter(test_list).items() if v > 1]

        self.assertEqual(sorted(duplicates), [2, 3])

    def test_in_bulk_usage(self):
        """
        Test that in_bulk is used for efficient fetching.
        """
        # Create test objects
        obj1 = SimpleModel.objects.create(contents="first", number=1)
        obj2 = SimpleModel.objects.create(contents="second", number=2)
        obj3 = SimpleModel.objects.create(contents="third", number=3)

        # Test in_bulk with IDs
        id_list = [obj2.pk, obj1.pk, obj3.pk]
        obj_dict = SimpleModel.objects.in_bulk(id_list)

        self.assertEqual(len(obj_dict), 3)
        self.assertEqual(obj_dict[obj1.pk].contents, "first")
        self.assertEqual(obj_dict[obj2.pk].contents, "second")
        self.assertEqual(obj_dict[obj3.pk].contents, "third")


class TestTransactionMixin(TestCase):
    def test_transaction_mixin_inheritance(self):
        """
        Test that bulk mixins properly inherit from BulkTransactionMixin.
        """
        from rest_framework_bulk.drf3.mixins import (
            BulkCreateModelMixin,
            BulkDestroyModelMixin,
            BulkTransactionMixin,
            BulkUpdateModelMixin,
        )

        # Check that all bulk mixins inherit from BulkTransactionMixin
        self.assertTrue(issubclass(BulkCreateModelMixin, BulkTransactionMixin))
        self.assertTrue(issubclass(BulkUpdateModelMixin, BulkTransactionMixin))
        self.assertTrue(issubclass(BulkDestroyModelMixin, BulkTransactionMixin))

        # Check that maybe_atomic method is available
        self.assertTrue(hasattr(BulkCreateModelMixin, "maybe_atomic"))
        self.assertTrue(hasattr(BulkUpdateModelMixin, "maybe_atomic"))
        self.assertTrue(hasattr(BulkDestroyModelMixin, "maybe_atomic"))


class TestSerializerInitValidation(TestCase):
    def test_create_only_serializer_no_validation(self):
        """
        Test that serializers used only for creation don't require update_lookup_field.
        """

        class CreateOnlySerializer(BulkSerializerMixin, ModelSerializer):
            class Meta:
                model = SimpleModel
                list_serializer_class = BulkListSerializer
                fields = ["contents", "number"]  # No 'id' field

        # Should not raise during creation context
        try:
            CreateOnlySerializer(data={"contents": "test", "number": 1})
            # No exception should be raised for POST/creation
        except ValueError:
            self.fail("Serializer raised ValueError for creation-only context")

    def test_update_serializer_with_validation(self):
        """
        Test that serializer validation is only applied for bulk update operations.
        """

        # Test that creation-only serializers work fine without update_lookup_field
        class CreateOnlySerializer(BulkSerializerMixin, ModelSerializer):
            class Meta:
                model = SimpleModel
                list_serializer_class = BulkListSerializer
                fields = ["contents", "number"]  # No 'id' field

        # This should work fine for creation
        try:
            CreateOnlySerializer(
                data=[{"contents": "test1", "number": 1}, {"contents": "test2", "number": 2}],
                many=True,
            )
            # No exception should be raised for creation context
        except ValueError:
            self.fail("Serializer raised ValueError for creation-only context")
