"""Scope a dated Realtime comparison to the initial owning parent readback."""

from types import FunctionType, ModuleType
import json

from daily_partitions import canonical


UTC_POSTMASTER_START_DAY = "select (pg_postmaster_start_time() at time zone 'UTC')::date"


def prepare(original, archive, archive_pin, *, archived_startup_day, restored_source_day=None):
    """Retain the archived Full25 authority and derive its dated view once."""
    reviewed = original.reviewed_fields(archive, archive_pin)
    captured = json.loads(archive)
    archived_view = original.comparable(canonical(captured, anchor=archived_startup_day))[0]

    def verify(cur, value, inputs, fingerprint):
        if inputs.get('parent_catalogue_equivalence') != reviewed:
            raise ValueError('GLOBAL_REALTIME_EXACT_ARCHIVED_REVIEW_REQUIRED')
        live_view = original.comparable(value)[0]
        if restored_source_day is None and live_view == {key: reviewed[key] for key in ('groups', 'guard')}:
            return original.verify(cur, value, inputs, fingerprint)
        live_day, = cur.execute(UTC_POSTMASTER_START_DAY).fetchone()

        # A cold restore keeps the partition bounds from the source cluster.
        # The caller supplies its observed source date only after checking the original BF.
        partition_day = live_day if restored_source_day is None else restored_source_day

        def comparable(actual):
            # Only the catalogue comparison uses the dated view. The actual
            # fingerprint and the subsequent live credit routine use raw rows.
            return original.comparable(canonical(actual, anchor=partition_day))

        target = original.verify
        scoped = FunctionType(target.__code__, dict(target.__globals__, comparable=comparable),
                              target.__name__, target.__defaults__, target.__closure__)
        result = scoped(cur, value, dict(inputs, parent_catalogue_equivalence={**reviewed, **archived_view}), fingerprint)
        receipt = dict(
            archived_startup_utc_day=archived_startup_day.isoformat(),
            current_postmaster_utc_day=live_day.isoformat(),
            archived_full25_groups=reviewed['groups'], current_full25_groups=live_view['groups'],
        )
        if restored_source_day is not None:
            receipt['restored_source_utc_day'] = partition_day.isoformat()
        return dict(result, realtime_daily_partitions=receipt)

    return verify


def bind_provider(provider, original, archive, archive_pin, *, archived_startup_day, restored_source_day=None):
    """Keep the frozen provider and admission gates intact in a private view."""
    if provider._automatic_parent_catalogue.__code__ != original.verify.__code__:
        raise ValueError('GLOBAL_REALTIME_EXACT_EXISTING_PROVIDER_COMPARATOR_REQUIRED')
    result = ModuleType(provider.__name__ + '.dated_parent')
    result.__dict__.update(vars(provider), __name__=result.__name__)
    result._automatic_parent_catalogue = prepare(original, archive, archive_pin,
                                                 archived_startup_day=archived_startup_day,
                                                 restored_source_day=restored_source_day)
    for name, value in vars(provider).items():
        if isinstance(value, FunctionType) and value.__globals__ is vars(provider):
            cloned = FunctionType(value.__code__, vars(result), value.__name__, value.__defaults__, value.__closure__)
            cloned.__kwdefaults__ = value.__kwdefaults__
            vars(result)[name] = cloned
    return result
