"""Independent design model for conserved cents; not bound to product SQL.

The Native source is an exact monetary total. Cost custody units are rational
and never count stock pieces. A transfer owns the rounded money it actually
takes; an unchanged invoice cannot silently move its cent to another SKU.
"""
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction as F


def exact_cents(value):
    value=F(value)*100
    if value.denominator!=1:raise ValueError('SOURCE_MUST_BE_EXACT_CENTS')
    return value.numerator


def rounded_integer(value):
    value=F(value);sign=-1 if value<0 else 1;value=abs(value)
    whole,remainder=divmod(value.numerator,value.denominator)
    return sign*(whole+(2*remainder>=value.denominator))


@dataclass(frozen=True)
class Cell:
    units:F
    cents:int


@dataclass(frozen=True)
class Fact:
    key:str
    kind:str
    root:str
    changes:tuple


class CostOwnership:
    def __init__(self):
        self.cells={};self.sources={};self.quantities={};self.floors={};self.facts=()

    def unique(self,key):
        if any(f.key==key for f in self.facts):raise ValueError('IMMUTABLE_FACT_ID_REUSED')

    def check(self,root,cells,source):
        if sum(c.units for c in cells.values())!=self.quantities[root]:raise ValueError('COST_UNITS_NOT_CONSERVED')
        if sum(c.cents for c in cells.values())!=source:raise ValueError('SOURCE_CENTS_NOT_CONSERVED')
        if any(c.units<0 or(c.units==0 and c.cents!=0)for c in cells.values()):raise ValueError('CUSTODY_CAPACITY')

    def origin(self,key,root,scope,units,*,native_floor):
        self.unique(key);units=F(units);floor=exact_cents(native_floor)
        if root in self.cells or units<=0 or floor>0:raise ValueError('NEW_COST_ROOT_REQUIRED')
        self.quantities[root]=units;self.floors[root]=floor;self.sources[root]=0
        self.cells[root]={scope:Cell(units,0)};self.facts+=(Fact(key,'ORIGIN',root,((scope,units,0),)),)

    def price(self,key,root,total):
        total=exact_cents(total)
        if total<self.floors[root]:raise ValueError('UNCHANGED_NATIVE_RECOVERY_FLOOR')
        if total==self.sources[root]:return None
        self.unique(key);before=self.cells[root];after={};cumulative_units=F(0);last=0
        for scope,cell in sorted(before.items()):
            cumulative_units+=cell.units
            cumulative=rounded_integer(total*cumulative_units/self.quantities[root])
            after[scope]=Cell(cell.units,cumulative-last);last=cumulative
        self.check(root,after,total)
        changes=tuple((scope,F(0),cell.cents-before[scope].cents)for scope,cell in after.items()if cell.cents!=before[scope].cents)
        fact=Fact(key,'SOURCE_PRICE',root,changes)
        self.cells[root]=after;self.sources[root]=total;self.facts+=(fact,);return fact

    def transfer(self,key,root,source,target,units):
        self.unique(key);units=F(units);before=self.cells[root]
        src=before.get(source,Cell(F(0),0));dst=before.get(target,Cell(F(0),0))
        if source==target or units<=0 or units>src.units:raise ValueError('CUSTODY_CAPACITY')
        amount=rounded_integer(F(src.cents)*units/src.units)
        after=dict(before);after[source]=Cell(src.units-units,src.cents-amount);after[target]=Cell(dst.units+units,dst.cents+amount)
        self.check(root,after,self.sources[root])
        fact=Fact(key,'TRANSFER',root,((source,-units,-amount),(target,units,amount)))
        self.cells[root]=after;self.facts+=(fact,);return fact

    def buckets(self,root,scope,inventory_units):
        cell=self.cells[root][scope];inventory_units=F(inventory_units)
        if inventory_units<0 or inventory_units>cell.units:raise ValueError('CUSTODY_CAPACITY')
        owned=0 if cell.units==0 else rounded_integer(F(cell.cents)*inventory_units/cell.units)
        return tuple(Decimal(v)/100 for v in(cell.cents,owned,cell.cents-owned))
