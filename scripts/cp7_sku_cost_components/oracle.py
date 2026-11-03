"""Independent rational cost ownership model; no SQL or authoritative reads.

This is a design oracle, not a transaction engine or an admission receipt.
Money is rounded once per financial scope; posted fractions stay immutable.
"""
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction as F


def cents(value):
    value=F(value)*100
    sign=-1 if value<0 else 1;value=abs(value)
    whole,remainder=divmod(value.numerator,value.denominator)
    rounded=whole+(2*remainder>=value.denominator)
    return Decimal(sign*rounded)/100


def normalized(values):
    result={}
    for key,value in values:result[key]=result.get(key,F(0))+F(value)
    return tuple(sorted((key,value)for key,value in result.items()if value))


@dataclass(frozen=True)
class Bundle:
    pieces:tuple=()
    costs:tuple=()

    @classmethod
    def make(cls,pieces=(),costs=()):return cls(normalized(pieces),normalized(costs))

    @property
    def quantity(self):return sum((value for _,value in self.pieces),F(0))

    def scaled(self,factor):return Bundle.make(((k,v*factor)for k,v in self.pieces),((k,v*factor)for k,v in self.costs))

    def plus(self,other):return Bundle.make(self.pieces+other.pieces,self.costs+other.costs)

    def minus(self,other):return self.plus(other.scaled(F(-1)))

    def require_nonnegative(self):
        if any(v<0 for _,v in self.pieces+self.costs):raise ValueError('MODELED_COMPONENT_CAPACITY')
        return self


@dataclass(frozen=True)
class Cost:
    quantity:F
    total:F
    native_floor:F
    po:str|None=None
    dependency_open:bool=False

    @property
    def unit(self):return self.total/self.quantity


@dataclass(frozen=True)
class Fact:
    kind:str
    key:str
    source:tuple|None
    target:tuple|None
    bundle:Bundle
    booked:Decimal
    parent:str|None=None
    cost_roots:tuple=()


class Model:
    """Explicitly modeled state; external Native guards are not simulated away."""
    def __init__(self):
        self.pools={};self.base={};self.costs={};self.facts=();self.sales={};self.returns={};self.conversions={}

    @staticmethod
    def scope(product,po):return ('PO',po)if po is not None else('NONPO',product)

    def value(self,bundle,costs=None):
        values=self.costs if costs is None else costs
        return sum((quantity*self.base[key][0]for key,quantity in bundle.pieces),F(0))+sum(
            (quantity*values[key].unit for key,quantity in bundle.costs),F(0))

    def pool(self,key):return self.pools.get(key,Bundle())

    def add_root(self,key,pool,quantity,unit,po=None):
        if key in self.base or key in self.costs or F(quantity)<=0 or F(unit)<0:
            raise ValueError('MODELED_NEW_POSITIVE_ROOT_REQUIRED')
        self.base[key]=(F(unit),po,F(quantity));self.pools[pool]=self.pool(pool).plus(Bundle.make([(key,F(quantity))]))

    def select(self,pool,quantity):
        current=self.pool(pool);quantity=F(quantity)
        if quantity<=0 or quantity>current.quantity:raise ValueError('MODELED_POSITIVE_PHYSICAL_CAPACITY')
        return current.scaled(quantity/current.quantity)

    def unique(self,key):
        if any(f.key==key for f in self.facts):raise ValueError('MODELED_FACT_ID_REUSED')

    def convert(self,key,source,target,quantity,children):
        self.unique(key)
        if source==target:raise ValueError('MODELED_DISTINCT_POOL_REQUIRED')
        carried=self.select(source,quantity);new_costs={}
        for root,qty,native_floor,po in children:
            if root in self.base or root in self.costs or root in new_costs or F(qty)<=0 or F(native_floor)<0:
                raise ValueError('MODELED_UNIQUE_NATIVE_COST_ALLOCATION')
            new_costs[root]=Cost(F(qty),F(0),-F(native_floor),po)
        if sum((c.quantity for c in new_costs.values()),F(0))!=F(quantity):
            raise ValueError('MODELED_ALL_PHYSICAL_CHILD_ALLOCATIONS_REQUIRED')
        own=Bundle.make(costs=[(root,c.quantity)for root,c in new_costs.items()])
        fact=Fact('CONVERT',key,source,target,carried,cents(self.value(carried)),cost_roots=tuple(new_costs))
        self.pools[source]=self.pool(source).minus(carried).require_nonnegative()
        self.pools[target]=self.pool(target).plus(carried).plus(own)
        self.costs.update(new_costs);self.conversions[key]=fact;self.facts+=(fact,)
        return fact

    def sell(self,key,pool,quantity):
        self.unique(key);carried=self.select(pool,quantity)
        fact=Fact('SALE',key,pool,None,carried,cents(self.value(carried)))
        self.pools[pool]=self.pool(pool).minus(carried).require_nonnegative()
        self.sales[key]=(fact,carried);self.facts+=(fact,);return fact

    def return_sale(self,key,sale,quantity,target=None):
        self.unique(key);fact,remaining=self.sales[sale];quantity=F(quantity)
        if quantity<=0 or quantity>remaining.quantity:raise ValueError('MODELED_RETURN_CAPACITY')
        target=fact.source if target is None else target
        if target[0]!=fact.source[0]:raise ValueError('MODELED_RETURN_PRODUCT_CHANGED')
        restored=fact.bundle.scaled(quantity/fact.bundle.quantity)
        remainder=remaining.minus(restored).require_nonnegative()
        # This oracle returns the whole scoped FG target change, not a
        # rounded per-item average copied from the sale snapshot.
        before=self.books();self.pools[target]=self.pool(target).plus(restored)
        self.sales[sale]=(fact,remainder)
        after=self.books();amount=sum((row['FG']-before.get(scope,dict(FG=Decimal(0)))['FG']for scope,row in after.items()),Decimal(0))
        returned=Fact('RETURN',key,None,target,restored,amount,parent=sale)
        self.returns[key]=returned;self.facts+=(returned,);return returned

    def inverse_return(self,key,returned):
        self.unique(key);old=self.returns[returned]
        target=self.pool(old.target).minus(old.bundle).require_nonnegative()
        sale,remaining=self.sales[old.parent]
        fact=Fact('RETURN_INVERSE',key,old.target,None,old.bundle,cents(self.value(old.bundle)),parent=returned)
        self.pools[old.target]=target;self.sales[old.parent]=(sale,remaining.plus(old.bundle))
        del self.returns[returned];self.facts+=(fact,);return fact

    def inverse_sale(self,key,sale):
        self.unique(key);old,remaining=self.sales[sale]
        if any(f.parent==sale for f in self.returns.values())or remaining!=old.bundle:
            raise ValueError('MODELED_ACTIVE_RETURN_BLOCKS_SALE_INVERSE')
        fact=Fact('SALE_INVERSE',key,None,old.source,old.bundle,cents(self.value(old.bundle)),parent=sale)
        self.pools[old.source]=self.pool(old.source).plus(old.bundle);del self.sales[sale];self.facts+=(fact,);return fact

    def revalue_cost(self,key,total,*,dependency_open=True):
        old=self.costs[key];total=F(total)
        if total<old.native_floor:raise ValueError('MODELED_UNCHANGED_NATIVE_FIRST_PART_RECOVERY_LIMIT')
        new=dict(self.costs);new[key]=Cost(old.quantity,total,old.native_floor,old.po,dependency_open)
        if any(self.value(bundle,new)<0 for bundle in self.pools.values()):
            raise ValueError('MODELED_NEGATIVE_POOL_VALUE')
        self.costs=new

    def revalue_base(self,key,unit):
        old=self.base[key];unit=F(unit)
        if unit<0:raise ValueError('MODELED_NEGATIVE_BASE_COST')
        proposed=dict(self.base);proposed[key]=(unit,old[1],old[2])
        if any(sum((q*proposed[k][0]for k,q in b.pieces),F(0))+
               sum((q*self.costs[k].unit for k,q in b.costs),F(0))<0 for b in self.pools.values()):
            raise ValueError('MODELED_NEGATIVE_POOL_VALUE')
        self.base=proposed

    def inverse_conversion(self,key,conversion):
        self.unique(key);old=self.conversions[conversion]
        if any(self.costs[root].dependency_open or self.costs[root].total for root in old.cost_roots):
            raise ValueError('MODELED_OPEN_NATIVE_COST_DEPENDENCY')
        own=Bundle.make(costs=[(root,self.costs[root].quantity)for root in old.cost_roots])
        target=self.pool(old.target).minus(old.bundle).minus(own).require_nonnegative()
        fact=Fact('CONVERSION_INVERSE',key,old.target,old.source,old.bundle,cents(self.value(old.bundle)),parent=conversion)
        self.pools[old.target]=target;self.pools[old.source]=self.pool(old.source).plus(old.bundle)
        for root in old.cost_roots:del self.costs[root]
        del self.conversions[conversion];self.facts+=(fact,);return fact

    def books(self):
        raw={}
        def add(product,bundle,kind):
            for root,quantity in bundle.pieces:
                unit,po,_=self.base[root];scope=self.scope(product,po)
                raw.setdefault(scope,dict(FG=F(0),COGS=F(0)))[kind]+=quantity*unit
            for root,quantity in bundle.costs:
                cost=self.costs[root];scope=self.scope(product,cost.po)
                raw.setdefault(scope,dict(FG=F(0),COGS=F(0)))[kind]+=quantity*cost.unit
        for pool,bundle in self.pools.items():add(pool[0],bundle,'FG')
        for fact,remaining in self.sales.values():add(fact.source[0],remaining,'COGS')
        return {scope:dict(HPP=cents(row['FG']+row['COGS']),FG=cents(row['FG']),COGS=cents(row['COGS']),
            residual=cents(row['FG']+row['COGS'])-cents(row['FG'])-cents(row['COGS']))for scope,row in raw.items()}

    def conservation(self):
        all_bundles=list(self.pools.values())+[remaining for _,remaining in self.sales.values()]
        held=Bundle()
        for bundle in all_bundles:held=held.plus(bundle)
        if dict(held.pieces)!={k:q for k,(_,_,q)in self.base.items()}:raise ValueError('MODELED_BASE_PIECES_NOT_CONSERVED')
        if dict(held.costs)!={k:c.quantity for k,c in self.costs.items()}:raise ValueError('MODELED_ADDITIONAL_COST_UNITS_NOT_CONSERVED')
        return dict(base_roots=len(self.base),cost_roots=len(self.costs),
            physical_quantity=sum((q for _,_,q in self.base.values()),F(0)),
            extra_cost=sum((c.total for c in self.costs.values()),F(0)),actual_ERP_cases=0)
