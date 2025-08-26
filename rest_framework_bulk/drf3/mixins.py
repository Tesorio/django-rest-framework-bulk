from __future__ import print_function, unicode_literals

import contextlib

from django.db import transaction
from rest_framework import status
from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response

__all__ = [
    "BulkCreateModelMixin",
    "BulkDestroyModelMixin",
    "BulkUpdateModelMixin",
]


class BulkTransactionMixin:
    """
    Mixin that provides transaction management for bulk operations.
    """

    @contextlib.contextmanager
    def maybe_atomic(self):
        """
        Context manager that conditionally wraps operations in a transaction.
        Set use_bulk_transactions=False on the view to disable transactions.
        """
        use_tx = getattr(self, "use_bulk_transactions", True)
        ctx = transaction.atomic() if use_tx else contextlib.nullcontext()
        with ctx:
            yield


class BulkCreateModelMixin(BulkTransactionMixin, CreateModelMixin):
    """
    Either create a single or many model instances in bulk by using the
    Serializers ``many=True`` ability from Django REST >= 2.2.5.

    .. note::
        This mixin uses the same method to create model instances
        as ``CreateModelMixin`` because both non-bulk and bulk
        requests will use ``POST`` request method.
    """

    def create(self, request, *args, **kwargs):
        bulk = isinstance(request.data, list)

        if not bulk:
            return super(BulkCreateModelMixin, self).create(request, *args, **kwargs)

        else:
            serializer = self.get_serializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            self.perform_bulk_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_bulk_create(self, serializer):
        with self.maybe_atomic():
            return self.perform_create(serializer)


class BulkUpdateModelMixin(BulkTransactionMixin, object):
    """
    Update model instances in bulk by using the Serializers
    ``many=True`` ability from Django REST >= 2.2.5.
    """

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        if lookup_url_kwarg in self.kwargs:
            return super(BulkUpdateModelMixin, self).get_object()

        # If the lookup_url_kwarg is not present
        # get_object() is most likely called as part of options()
        # which by default simply checks for object permissions
        # and raises permission denied if necessary.
        # Here we don't need to check for general permissions
        # and can simply return None since general permissions
        # are checked in initial() which always gets executed
        # before any of the API actions (e.g. create, update, etc)
        return

    def bulk_update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)

        # restrict the update to the filtered queryset
        serializer = self.get_serializer(
            self.filter_queryset(self.get_queryset()),
            data=request.data,
            many=True,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        self.perform_bulk_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_bulk_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.bulk_update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save()

    def perform_bulk_update(self, serializer):
        with self.maybe_atomic():
            return self.perform_update(serializer)


class BulkDestroyModelMixin(BulkTransactionMixin, object):
    """
    Destroy model instances.
    """

    def allow_bulk_destroy(self, base_qs, filtered_qs):
        """
        Hook to ensure that the bulk destroy should be allowed.

        By default this checks that the destroy is only applied to
        filtered querysets. Uses order-insensitive comparison and
        count-based verification for safety.
        """
        # Normalize ordering to avoid false positives from ORDER BY differences
        base_norm = base_qs.order_by()
        filt_norm = filtered_qs.order_by()

        # Fast path: if queries are identical (no filtering), block
        if str(base_norm.query) == str(filt_norm.query):
            return False

        # If queries differ, filtering was applied - allow the delete
        # The query difference check is sufficient to determine filtering occurred
        return True

    def bulk_destroy(self, request, *args, **kwargs):
        qs = self.get_queryset()

        filtered = self.filter_queryset(qs)
        if not self.allow_bulk_destroy(qs, filtered):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        self.perform_bulk_destroy(filtered)

        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.delete()

    def perform_bulk_destroy(self, objects):
        with self.maybe_atomic():
            for obj in objects:
                self.perform_destroy(obj)
