"""Exact restoration including every definition/owner/ACL, with raw diagnostics.

The frozen reader's public function aggregate orders by constant 1. Compare all
original signature/hash pairs in canonical order, retaining the raw observation.
The accepted reader and runner, data, members and hashes remain untouched.
"""
from cp7_catalog_state import canonical_public_state

def capture(cur,boundary_reader,public_reader,function_reader):
 return dict(boundary=boundary_reader(cur),public=public_reader(cur),functions=function_reader(cur))

def prove(cur,before,boundary_reader,public_reader,function_reader,report):
 after=capture(cur,boundary_reader,public_reader,function_reader)
 components=dict(erp_platform_auth_schema_acl=after['boundary']==before['boundary'],
  all_public_catalog_members_and_row_hashes=canonical_public_state(after['public'])==canonical_public_state(before['public']),
  erp_public_auth_function_definitions_owners_acls=after['functions']==before['functions'])
 report['restore_components']=components
 report['restore_raw_public_equal']=after['public']==before['public']
 if after['public']!=before['public']:
  report['restore_raw_public_difference']=dict(before=before['public'],after=after['public'])
  report['restore_raw_public_difference_is_only_pair_order']=components['all_public_catalog_members_and_row_hashes']
 if after['boundary']!=before['boundary']:report['restore_boundary_difference']=dict(before=before['boundary'],after=after['boundary'])
 if after['functions']!=before['functions']:report['restore_function_difference']=dict(before=before['functions'],after=after['functions'])
 return all(components.values())
