"""Four Native controls for the installation inventory, not fixture policies."""
from copy import deepcopy
from decimal import Decimal
import cp7_install_legacy_inventory as inventory
import cp7_ow14b_rule_cases as fabric
from cp7_ow04_restore_bundle import _data,_catalog_rows

IDS=('OW14B_INSTALL_IDENTITY_UNIT_SIX_DECIMALS',
     'OW14B_INSTALL_PINNED_RULE_OLD_REFERENCE',
     'OW14B_INSTALL_KNOWN_ZERO_UNKNOWN',
     'OW14B_INSTALL_SOURCE_AND_REFERENCE_DRIFT_REFUSED')


def observe(cur):
    fabric.b.api.admin(cur)
    before=_data(cur);catalog=_catalog_rows(cur)
    captured=inventory.capture(cur);preview=inventory.preview_active_rules(cur,captured)
    assert _data(cur)==before and _catalog_rows(cur)==catalog
    return captured,preview


def row(preview,f):return next(x for x in preview['rows']if x['material_id']==f['material'])


def cases(cur,today):
    def exact():
        f=fabric.factory(cur,today,history=False,minimum='500.123456')
        captured,preview=observe(cur)
        native=next(x for x in captured['rows']if x['material_id']==f['material'])
        actual=row(preview,f)
        assert Decimal(native['minimum_stock_qty'])==Decimal('500.123456')
        assert actual['unit_code']==native['unit_code']and actual['sku']==native['sku']
        assert actual['fabric_rule']is None and actual['basis']=='MANUAL'
        assert Decimal(actual['point'])==Decimal('500.123456')
        return dict(status='PASS',exact_id_unit_six_decimal_reference=True,
            official_inherited_rule=True,no_inventory_cache_or_business_writes=True)

    def pinned():
        f=fabric.factory(cur,today,history=False,minimum='500.123456')
        actor=fabric.master.role_actor(cur,'OWNER')
        fabric.save(cur,fabric.payload(f,rule='LEGACY_MINIMUM',reference='500.123456'),subject=actor)
        fabric.reference(cur,f,'900.654321')
        captured,preview=observe(cur);actual=row(preview,f)
        assert Decimal(actual['legacy_minimum_qty'])==Decimal('900.654321')
        assert actual['fabric_rule']=='LEGACY_MINIMUM'and Decimal(actual['point'])==Decimal('500.123456')
        return dict(status='PASS',new_legacy_reference_separate_from_pinned_active_rule=True,
            no_choice_or_revision_created=True,official_engine_only=True)

    def zero_unknown():
        actor=fabric.master.role_actor(cur,'OWNER')
        zero=fabric.factory(cur,today,history=False,minimum='0')
        fabric.save(cur,fabric.payload(zero,rule='LEGACY_MINIMUM',reference='0'),subject=actor)
        unknown=fabric.factory(cur,today,history=False,minimum='700')
        fabric.save(cur,fabric.payload(unknown,rule='FORMULA',reference='700',lead=None),subject=actor)
        captured,preview=observe(cur);z,u=row(preview,zero),row(preview,unknown)
        assert z['basis']=='MANUAL'and Decimal(z['point'])==0 and z['state']=='NO_POINT'
        assert u['fabric_rule']=='FORMULA'and u['point']is None and u['basis']=='NO_USAGE'
        return dict(status='PASS',chosen_zero_known=True,unready_formula_unknown=True,
            old_minimum_not_reactivated=True,no_substitute_calculation=True)

    def refused():
        f=fabric.factory(cur,today,history=False,minimum='500.123456')
        captured,_=observe(cur);held=_data(cur)
        forged=deepcopy(captured);forged['rows'][0]['unit_code']='FORGED'
        try:inventory.assert_preserved(cur,forged)
        except ValueError as e:assert str(e)=='OW14B_TRUSTED_INVENTORY_REQUIRED'
        else:raise AssertionError('FORGED_INVENTORY_ACCEPTED')
        assert _data(cur)==held
        fabric.reference(cur,f,'501.123456')
        changed=_data(cur)
        try:inventory.assert_preserved(cur,captured)
        except ValueError as e:assert str(e)=='OW14B_NATIVE_REFERENCE_CHANGED_DURING_INSTALL'
        else:raise AssertionError('CHANGED_NATIVE_REFERENCE_ACCEPTED')
        assert _data(cur)==changed
        return dict(status='PASS',forged_inventory_refused=True,real_changed_reference_refused=True,
            no_write_by_refusals=True)
    return list(zip(IDS,(exact,pinned,zero_unknown,refused)))
