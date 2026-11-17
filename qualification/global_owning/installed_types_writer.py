"""Observe types on the exact existing Global writer path in private CI."""

from types import FunctionType
import re

from . import installed_types


ANCHOR = "            _global_auth.begin(conn,cur,package.boundary.ADMIN,package.boundary.PRIMARY_ADMIN,\n"
OBSERVE = '''            try:
                report['installed_public_types'] = measured(timings,'INSTALLED_PUBLIC_TYPES',_observe_installed_types,conn,cur,STATE,report)
            except Exception as error:
                report['installed_public_types'] = dict(status='INCOMPLETE', error_type=type(error).__name__)
                _retain_installed_types_failure(error)
'''


def bind(owner, source, report_io, lifecycle, candidate):
    # The original owning writer has already matched the retained source and
    # complete inverse derivation. Only its one committed observation is added.
    inner = owner.run_inner
    namespace = inner.__globals__
    code = report_io.function_code(source, inner.__code__.co_filename, 'run_inner')
    installed_types.require(owner.run.__globals__ is namespace and inner.__code__ == code
                            and source.count(ANCHOR) == 1 and OBSERVE not in source
                            and '_observe_installed_types' not in namespace,
                            'CP7_INSTALLED_TYPES_EXACT_COMMITTED_WRITER_REQUIRED')
    changed = source.replace(ANCHOR, OBSERVE + ANCHOR, 1)
    installed_types.require(changed.replace(OBSERVE, '', 1) == source,
                            'CP7_INSTALLED_TYPES_WRITER_SOURCE_CHANGED')

    def observe(conn, cur, state, report):
        foundation = report['preseal_foundation']
        installed_types.require(foundation.get('status') == 'VERIFIED_ON_EXISTING_INSTALLER_AFTER_COMMIT',
                                'CP7_INSTALLED_TYPES_COMMITTED_FOUNDATION_REQUIRED')
        return installed_types.collect(conn, cur, package=namespace['package'], lifecycle=lifecycle,
                                       state=state, preseal_census=foundation['after_rows_and_sequences'],
                                       candidate=candidate, output=owner.output.parent)

    def retain_failure(error):
        from traceback import format_exception

        output = owner.output.parent
        with (owner.output.parent / 'CP7_INSTALLED_TYPES_FIRST_FAILURE.txt').open('x', encoding='utf-8') as stream:
            stream.writelines(format_exception(error))
        tag = re.match(r'^(?:CP7_INSTALLED_TYPES_|GENERATED_TYPES_)[A-Z0-9_]{5,95}\b', str(error))
        with (output / 'CP7_INSTALLED_TYPES_STATUS.txt').open('x', encoding='ascii') as stream:
            stream.write((tag[0] if tag else 'CP7_INSTALLED_TYPES_ORIGINAL_RETAINED_IN_RUNNER') + '\n')

    bound = report_io.function_code(changed, inner.__code__.co_filename, 'run_inner')
    namespace.update(_observe_installed_types=observe, _retain_installed_types_failure=retain_failure)
    namespace['run_inner'] = FunctionType(bound, namespace, 'run_inner', inner.__defaults__)
