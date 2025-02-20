from collections import defaultdict

from django.contrib.contenttypes.fields import GenericForeignKey as StandardGenericForeignKey


class GenericForeignKey(StandardGenericForeignKey):
    def get_prefetch_queryset(self, instances, queryset=None):
        if queryset is None:
            return self.get_prefetch_querysets(instances)
        return self.get_prefetch_querysets(instances, queryset)

    def get_prefetch_querysets(self, instances, querysets=None):
        custom_queryset_dict = {}
        if querysets is not None:
            for queryset in querysets:
                ct_id = self.get_content_type(
                    model=queryset.query.model, using=queryset.db
                ).pk
                if ct_id in custom_queryset_dict:
                    raise ValueError(
                        "Only one queryset is allowed for each content type."
                    )
                custom_queryset_dict[ct_id] = queryset

        # For efficiency, group the instances by content type and then do one
        # query per model
        fk_dict = defaultdict(set)
        # We need one instance for each group in order to get the right db:
        instance_dict = {}
        ct_attname = self.model._meta.get_field(self.ct_field).attname
        for instance in instances:
            # We avoid looking for values if either ct_id or fkey value is None
            ct_id = getattr(instance, ct_attname)
            if ct_id is not None:
                fk_val = getattr(instance, self.fk_field)
                if fk_val is not None:
                    fk_dict[ct_id].add(fk_val)
                    instance_dict[ct_id] = instance

        ret_val = []
        for ct_id, fkeys in fk_dict.items():
            if ct_id in custom_queryset_dict:
                # Return values from the custom queryset, if provided.
                ret_val.extend(custom_queryset_dict[ct_id].filter(pk__in=fkeys))
            else:
                instance = instance_dict[ct_id]
                ct = self.get_content_type(id=ct_id, using=instance._state.db)
                ret_val.extend(ct.get_all_objects_for_this_type(pk__in=fkeys))

        # For doing the join in Python, we have to match both the FK val and the
        # content type, so we use a callable that returns a (fk, class) pair.
        def gfk_key(obj):
            ct_id = getattr(obj, ct_attname)
            if ct_id is None:
                return None
            else:
                model = self.get_content_type(
                    id=ct_id, using=obj._state.db
                ).model_class()
                return (
                    model._meta.pk.get_prep_value(getattr(obj, self.fk_field)),
                    model,
                )

        return (
            ret_val,
            lambda obj: (obj.pk, obj.__class__),
            gfk_key,
            True,
            self.name,
            False,
        )
