from __future__ import print_function, unicode_literals

import inspect
from collections import Counter

from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ListSerializer

__all__ = [
    "BulkListSerializer",
    "BulkSerializerMixin",
]


class BulkSerializerMixin(object):
    def __init__(self, *args, **kwargs):
        super(BulkSerializerMixin, self).__init__(*args, **kwargs)

        # Only validate update_lookup_field for bulk update operations
        view = self.context.get("view") if hasattr(self, "context") else None
        request = getattr(view, "request", None) if view else None
        method = getattr(request, "method", "") if request else ""

        # Check if this is a bulk update scenario
        if method in ("PUT", "PATCH") and isinstance(self.root, BulkListSerializer):
            id_attr = getattr(self.Meta, "update_lookup_field", "id")
            if id_attr not in self.fields:
                raise ValueError(
                    f"update_lookup_field '{id_attr}' is not present in serializer fields. "
                    f"Available fields: {list(self.fields.keys())}"
                )

    def to_internal_value(self, data):
        ret = super(BulkSerializerMixin, self).to_internal_value(data)

        id_attr = getattr(self.Meta, "update_lookup_field", "id")
        request_method = getattr(getattr(self.context.get("view"), "request"), "method", "")

        # add update_lookup_field field back to validated data
        # since super by default strips out read-only fields
        # hence id will no longer be present in validated_data
        if isinstance(self.root, BulkListSerializer) and request_method in ("PUT", "PATCH"):
            # Field existence already validated in __init__ for update operations
            id_field = self.fields[id_attr]
            id_value = id_field.get_value(data)
            ret[id_attr] = id_value

        return ret


class BulkListSerializer(ListSerializer):
    update_lookup_field = "id"

    def update(self, queryset, all_validated_data):
        id_attr = getattr(self.child.Meta, "update_lookup_field", "id")

        # Extract and validate IDs in O(n)
        try:
            id_list = [item[id_attr] for item in all_validated_data]
        except KeyError:
            raise ValidationError(f"Missing required field '{id_attr}' in one or more items.")

        # O(n) duplicate detection using Counter
        duplicates = [k for k, v in Counter(id_list).items() if v > 1]
        if duplicates:
            raise ValidationError(f"Duplicate {id_attr} values found in request: {duplicates}")

        # Build data map by ID
        data_by_id = {}
        for item in all_validated_data:
            key = item.pop(id_attr)
            if not (bool(key) and not inspect.isclass(key)):
                raise ValidationError(f"Invalid or missing {id_attr} values: [{key!r}]")
            data_by_id[key] = item

        # Single query using in_bulk; supports non-PK lookup via field_name
        obj_by_id = queryset.in_bulk(id_list, field_name=id_attr)

        # Check for missing objects
        missing = [i for i in id_list if i not in obj_by_id]
        if missing:
            raise ValidationError(f"Could not find objects with {id_attr} values: {missing}")

        # Build response preserving input order
        updated_objects = []
        for obj_id in id_list:
            obj = obj_by_id[obj_id]
            updated_objects.append(self.child.update(obj, data_by_id[obj_id]))

        return updated_objects
