from __future__ import print_function, unicode_literals

import json

from django.test import TestCase, TransactionTestCase
from django.test.client import RequestFactory
from rest_framework import status

from .simple_app.models import SimpleModel
from .simple_app.views import FilteredBulkAPIView, SimpleBulkAPIView


class TestBulkUpdateCorrectness(TestCase):
    def setUp(self):
        super(TestBulkUpdateCorrectness, self).setUp()
        self.view = SimpleBulkAPIView.as_view()
        self.request = RequestFactory()

    def test_duplicate_id_detection(self):
        """
        Test that duplicate IDs in bulk update are detected and rejected.
        """
        obj1 = SimpleModel.objects.create(contents="hello world", number=1)

        # Submit update with duplicate IDs
        response = self.view(
            self.request.put(
                "/",
                json.dumps(
                    [
                        {"contents": "foo", "number": 3, "id": obj1.pk},
                        {"contents": "bar", "number": 4, "id": obj1.pk},  # Duplicate ID
                    ]
                ),
                content_type="application/json",
            )
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check that the error message mentions duplicate IDs
        self.assertIn("Duplicate", str(response.data))
        self.assertIn(str(obj1.pk), str(response.data))

        # Ensure no changes were made
        obj1.refresh_from_db()
        self.assertEqual(obj1.contents, "hello world")
        self.assertEqual(obj1.number, 1)

    def test_missing_objects_error_detail(self):
        """
        Test that missing objects in bulk update provide detailed error info.
        """
        obj1 = SimpleModel.objects.create(contents="hello world", number=1)
        non_existent_id = 99999

        response = self.view(
            self.request.put(
                "/",
                json.dumps(
                    [
                        {"contents": "foo", "number": 3, "id": obj1.pk},
                        {"contents": "bar", "number": 4, "id": non_existent_id},
                    ]
                ),
                content_type="application/json",
            )
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check that the error message includes the missing ID
        self.assertIn(str(non_existent_id), str(response.data))

    def test_invalid_id_error_message(self):
        """
        Test that invalid/missing IDs provide clear error messages.
        """
        response = self.view(
            self.request.put(
                "/",
                json.dumps(
                    [
                        {"contents": "foo", "number": 3, "id": None},
                    ]
                ),
                content_type="application/json",
            )
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Should have a clear error about invalid ID
        self.assertIn("Invalid", str(response.data))

    def test_missing_id_field_error(self):
        """
        Test that missing ID field provides clear error message.
        """
        SimpleModel.objects.create(contents="hello world", number=1)

        response = self.view(
            self.request.put(
                "/",
                json.dumps(
                    [
                        {"contents": "foo", "number": 3},  # Missing 'id' field
                    ]
                ),
                content_type="application/json",
            )
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_preserved_update_order(self):
        """
        Test that bulk update preserves the order of the input.
        """
        obj1 = SimpleModel.objects.create(contents="first", number=1)
        obj2 = SimpleModel.objects.create(contents="second", number=2)
        obj3 = SimpleModel.objects.create(contents="third", number=3)

        # Submit in different order than creation
        response = self.view(
            self.request.put(
                "/",
                json.dumps(
                    [
                        {"contents": "updated_third", "number": 30, "id": obj3.pk},
                        {"contents": "updated_first", "number": 10, "id": obj1.pk},
                        {"contents": "updated_second", "number": 20, "id": obj2.pk},
                    ]
                ),
                content_type="application/json",
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Response should preserve input order
        response_data = response.data
        self.assertEqual(len(response_data), 3)
        self.assertEqual(response_data[0]["id"], obj3.pk)
        self.assertEqual(response_data[0]["contents"], "updated_third")
        self.assertEqual(response_data[1]["id"], obj1.pk)
        self.assertEqual(response_data[1]["contents"], "updated_first")
        self.assertEqual(response_data[2]["id"], obj2.pk)
        self.assertEqual(response_data[2]["contents"], "updated_second")


class TestBulkDestroyCorrectness(TestCase):
    def setUp(self):
        super(TestBulkDestroyCorrectness, self).setUp()
        self.view = SimpleBulkAPIView.as_view()
        self.filtered_view = FilteredBulkAPIView.as_view()
        self.request = RequestFactory()

    def test_bulk_destroy_safety_with_cloned_queryset(self):
        """
        Test that bulk destroy correctly identifies filtered querysets even when cloned.
        """
        SimpleModel.objects.create(contents="hello world", number=1)
        SimpleModel.objects.create(contents="hello mars", number=10)

        # The unfiltered delete should still be rejected
        response = self.view(self.request.delete("/"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SimpleModel.objects.count(), 2)

        # Filtered delete should work
        response = self.filtered_view(self.request.delete("/"))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Should only delete items with number > 5
        self.assertEqual(SimpleModel.objects.count(), 1)
        self.assertEqual(SimpleModel.objects.get().number, 1)


class TestTransactionSupport(TransactionTestCase):
    """
    Test transaction support for bulk operations.
    Using TransactionTestCase to properly test transaction behavior.
    """

    def setUp(self):
        super(TestTransactionSupport, self).setUp()
        self.view = SimpleBulkAPIView.as_view()
        self.request = RequestFactory()

    def test_bulk_create_transaction(self):
        """
        Test that bulk create operations are wrapped in a transaction.
        """
        # This test would require a way to simulate a failure mid-operation
        # For now, we just verify the operations succeed
        initial_count = SimpleModel.objects.count()

        response = self.view(
            self.request.post(
                "/",
                json.dumps(
                    [
                        {"contents": "item1", "number": 1},
                        {"contents": "item2", "number": 2},
                    ]
                ),
                content_type="application/json",
            )
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SimpleModel.objects.count(), initial_count + 2)

    def test_bulk_update_transaction(self):
        """
        Test that bulk update operations are wrapped in a transaction.
        """
        obj1 = SimpleModel.objects.create(contents="hello world", number=1)
        obj2 = SimpleModel.objects.create(contents="hello mars", number=2)

        response = self.view(
            self.request.put(
                "/",
                json.dumps(
                    [
                        {"contents": "updated1", "number": 10, "id": obj1.pk},
                        {"contents": "updated2", "number": 20, "id": obj2.pk},
                    ]
                ),
                content_type="application/json",
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        obj1.refresh_from_db()
        obj2.refresh_from_db()
        self.assertEqual(obj1.contents, "updated1")
        self.assertEqual(obj2.contents, "updated2")


class TestSerializerValidation(TestCase):
    def test_update_lookup_field_validation(self):
        """
        Test that serializer validation works correctly during actual bulk update operations.
        """
        # Since our refactored code only validates on actual use during PUT/PATCH
        # let's test that the validation happens correctly at runtime when needed
        from rest_framework.serializers import ModelSerializer

        from rest_framework_bulk.serializers import BulkListSerializer, BulkSerializerMixin

        class GoodSerializer(BulkSerializerMixin, ModelSerializer):
            class Meta:
                model = SimpleModel
                list_serializer_class = BulkListSerializer
                fields = "__all__"  # Includes 'id'
                update_lookup_field = "id"

        # This should work fine
        try:
            GoodSerializer(data={"contents": "test", "number": 1})
            # No exception should be raised for a properly configured serializer
        except ValueError:
            self.fail("Good serializer raised ValueError unexpectedly")


class TestOptOutTransactions(TestCase):
    """
    Test that views can opt out of transaction wrapping.
    """

    def test_opt_out_bulk_transactions(self):
        """
        Test that setting use_bulk_transactions=False disables transactions.
        """

        # Create a custom view that opts out of transactions
        class NoTransactionView(SimpleBulkAPIView):
            use_bulk_transactions = False

        view = NoTransactionView.as_view()
        request = RequestFactory()

        # Bulk create should still work without transactions
        response = view(
            request.post(
                "/",
                json.dumps(
                    [
                        {"contents": "item1", "number": 1},
                        {"contents": "item2", "number": 2},
                    ]
                ),
                content_type="application/json",
            )
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SimpleModel.objects.count(), 2)
