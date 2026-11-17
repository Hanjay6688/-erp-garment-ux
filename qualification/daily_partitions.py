"""Compare the exact daily Supabase Realtime partition family across test copies."""

from datetime import date, timedelta
import re


PARENT = 'realtime.messages'
STEM = PARENT + '_'
DAY_SUFFIX = re.compile(r'\d{4}_\d{2}_\d{2}')
DAY_TOKEN = re.compile(r'(?<!\w)messages_\d{4}_\d{2}_\d{2}(?!\d)')


def partition_name(day):
    return STEM + day.isoformat().replace('-', '_')


def expected_objects(name):
    short = name.split('.', 1)[1]
    topic_index = name + '_inserted_at_topic_idx'
    primary = name + '_pkey'
    return {
        'relations': (name, topic_index, primary),
        'columns': (
            *(name + ':' + column for column in ('binary_payload', 'event', 'extension', 'id', 'inserted_at',
                                                   'payload', 'private', 'topic', 'updated_at')),
            topic_index + ':inserted_at', topic_index + ':topic', primary + ':id', primary + ':inserted_at',
        ),
        'constraints': (name + ':' + short + '_pkey', name + ':messages_payload_exclusive'),
        'indexes': (topic_index, primary),
        'inheritance': (name + ':1', topic_index + ':1', primary + ':1'),
        'type_implementation': (name, name + '[]'),
        'types': (name, name + '[]'),
    }


def expected_range(day):
    following = day + timedelta(days=1)
    return f"FOR VALUES FROM ('{day.isoformat()} 00:00:00') TO ('{following.isoformat()} 00:00:00')"


def closed_references(row):
    if isinstance(row, str):
        return not DAY_TOKEN.search(row)
    if isinstance(row, (list, tuple)):
        return all(closed_references(item) for item in row)
    if isinstance(row, dict):
        return all(not DAY_TOKEN.search(name) and closed_references(item) for name, item in row.items())
    return True


def canonical_row(group, key, row, *, day, name, slot):
    if group == 'relations' and key == name:
        if (len(row) != 13 or row[0] != 'supabase_realtime_admin' or row[1:3] != ['r', 'p']
                or row[8] is not True or row[11] != expected_range(day)):
            raise ValueError('GLOBAL_REALTIME_EXACT_DAILY_PARTITION_REQUIRED')
        return [*row[:11], 'ONE_DAILY_MIDNIGHT_RANGE', row[12]]
    if group == 'inheritance':
        parents = {
            name + ':1': PARENT,
            name + '_inserted_at_topic_idx:1': PARENT + '_inserted_at_topic_index',
            name + '_pkey:1': PARENT + '_pkey',
        }
        if row != parents[key]:
            raise ValueError('GLOBAL_REALTIME_EXACT_ATTACHED_TABLE_AND_INDEXES_REQUIRED')
        return row
    if group == 'constraints':
        primary = key.endswith('_pkey')
        if row[8:10] != [name + '_pkey' if primary else None, name]:
            raise ValueError('GLOBAL_REALTIME_EXACT_PARTITION_CONSTRAINT_TARGETS_REQUIRED')
        positions = (8, 9)
    elif group == 'indexes':
        if not isinstance(row[0], str) or ' ON ' + name + ' USING btree ' not in row[0]:
            raise ValueError('GLOBAL_REALTIME_EXACT_PARTITION_INDEX_TARGET_REQUIRED')
        positions = (0,)
    elif group == 'type_implementation':
        expected = [name, '-', name + '[]'] if key == name else ['-', name, '-']
        if row[6:9] != expected:
            raise ValueError('GLOBAL_REALTIME_EXACT_COMPOSITE_AND_ARRAY_TARGETS_REQUIRED')
        positions = (6, 7, 8)
    else:
        positions = ()
    revised = list(row)
    for index in positions:
        value = revised[index]
        if isinstance(value, str):
            revised[index] = value.replace(name, slot).replace(name.split('.', 1)[1], slot.split('.', 1)[1])
    return revised


def canonical(catalogue, *, anchor):
    """Require the five observed days around the platform startup's UTC date."""
    if type(anchor) is not date or not date.min + timedelta(days=1) <= anchor <= date.max - timedelta(days=4):
        raise ValueError('GLOBAL_REALTIME_EXACT_STARTUP_UTC_DATE_REQUIRED')
    days = [anchor + timedelta(days=offset) for offset in range(-1, 4)]
    names = [partition_name(day) for day in days]
    daily = {key for key, _ in catalogue['relations']
             if key.startswith(STEM) and DAY_SUFFIX.fullmatch(key.removeprefix(STEM))}
    if daily != set(names):
        raise ValueError('GLOBAL_REALTIME_EXACT_FIVE_DAILY_PARTITIONS_REQUIRED')
    replacements = {}
    for index, (day, name) in enumerate(zip(days, names, strict=True)):
        slot = STEM + 'expected_day_' + str(index)
        for group, keys in expected_objects(name).items():
            for key in keys:
                replacements[group, key] = (day, name, slot)
    normalized = {}
    found = set()
    for group, entries in catalogue.items():
        rows = {}
        for key, row in entries:
            if STEM + 'expected_day_' in key:
                raise ValueError('GLOBAL_REALTIME_RESERVED_COMPARISON_IDENTITY')
            identity = group, key
            if identity in replacements:
                day, name, slot = replacements[identity]
                original_short, slot_short = (entry.split('.', 1)[1] for entry in (name, slot))
                key = key.replace(name, slot).replace(original_short, slot_short)
                row = canonical_row(group, identity[1], row, day=day, name=name, slot=slot)
                found.add(identity)
            if key in rows:
                raise ValueError('GLOBAL_REALTIME_DUPLICATE_CATALOGUE_IDENTITY')
            if DAY_TOKEN.search(key) or not closed_references(row):
                raise ValueError('GLOBAL_REALTIME_UNREVIEWED_DATE_REFERENCE')
            rows[key] = row
        normalized[group] = sorted(rows.items())
    if found != set(replacements):
        raise ValueError('GLOBAL_REALTIME_INCOMPLETE_DAILY_PARTITION_FOOTPRINT')
    return normalized
