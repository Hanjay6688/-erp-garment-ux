"""Derive only the two owning callers after exact terminal evidence is admitted."""

from hashlib import sha256

from .owner import verify_terminal


ORIGINAL = {
    "assembly.py": "83dde26124852056ae53974a5d8c649f307d58d1daacc5c349a804b63c4d690c",
    "component.py": "bf9a376506a9397b285ef61c5f78d4c1be53166d1f7bf5bc0473681391bb66cf",
}


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError("MANDOR_ADAPTER_EXACT_CALLER_ANCHOR_REQUIRED")
    return source.replace(old, new)


def derive(assembly_raw, component_raw, terminal_raw, terminal_sha256):
    verify_terminal(terminal_raw, terminal_sha256)
    for name, raw in (("assembly.py", assembly_raw), ("component.py", component_raw)):
        if sha256(raw).hexdigest() != ORIGINAL[name]:
            raise ValueError("MANDOR_ADAPTER_EXACT_PREDECESSOR_REQUIRED:" + name)
    assembly = assembly_raw.decode()
    assembly = replace_once(assembly, "import json,subprocess\n", """import json,subprocess,sys
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
""")
    loader = """
def load_review_adapter():
    directory = ROOT / 'scripts/current-mandor-afui-preparation/review_adapter'
    path = directory / '__init__.py'
    name = 'mandor_exact_review_adapter'
    package = sys.modules.get(name)
    if package is None:
        spec = spec_from_file_location(name, path, submodule_search_locations=[str(directory)])
        package = module_from_spec(spec)
        sys.modules[name] = package
        spec.loader.exec_module(package)
    require(Path(package.__file__).resolve() == path.resolve(), 'MANDOR_ADAPTER_PACKAGE_PATH_CHANGED')
    owner = import_module(name + '.owner')
    require(Path(owner.__file__).resolve() == (directory / 'owner.py').resolve(), 'MANDOR_ADAPTER_OWNER_PATH_CHANGED')
    return owner.Adapter(__TERMINAL_SHA__)


""".replace("__TERMINAL_SHA__", repr(terminal_sha256))
    assembly = replace_once(assembly, "class Assembly:", loader + "class Assembly:")
    assembly = replace_once(assembly, "        self.domain_modules=None\n",
                            "        self.domain_modules=None\n        self._adapter=load_review_adapter()\n")
    assembly = replace_once(assembly, "qualified_Afui_sources=pin(canonical(graph)),Mandor_sources=own,\n",
                            "qualified_Afui_sources=pin(canonical(graph)),Mandor_sources=own,\n"
                            "            Mandor_review_adapter=self._adapter.sources(),\n")
    assembly = replace_once(assembly, """        state=dict(contract=CONTRACT,sources=source,parent=qualified_Afui,Mandor=child,
            before=child['before'],after=child['after'])""", """        adapted, raw = self._adapter.install(cur, self.mandor, child)
        state=dict(contract=CONTRACT,sources=source,parent=qualified_Afui,Mandor=adapted,
            Original_Mandor=child,review_adapter_raw=raw,before=child['before'],after=adapted['after'])""")
    assembly = replace_once(assembly, """        require(state['before']==state['parent']['after']==state['Mandor']['before']and state['after']==state['Mandor']['after'],
            'MANDOR_ASSEMBLY_PARENT_OR_CHILD_CATALOGUE_BINDING_CHANGED')
        verified=self.mandor.verify(cur,state['Mandor'])""", """        original=state['Original_Mandor']
        require(state['before']==state['parent']['after']==original['before']and state['after']==state['Mandor']['after'],
            'MANDOR_ASSEMBLY_PARENT_OR_CHILD_CATALOGUE_BINDING_CHANGED')
        verified=self._adapter.verify(cur,self.mandor,original,state['Mandor'],state['review_adapter_raw'])""")
    assembly = replace_once(assembly, """        try:value=self.mandor.rollback_preuse(cur,state['Mandor'])""",
                            """        try:value=self._adapter.rollback(cur,self.mandor,state['Original_Mandor'],state['Mandor'],state['review_adapter_raw'])""")
    component = replace_once(component_raw.decode(), "        product.mandor,state['Mandor'],funding=funding,scope=scope)",
                             "        product,state,funding=funding,scope=scope)")
    output = {"assembly.py": assembly.encode(), "component.py": component.encode()}
    for name, source in output.items():
        compile(source, name, "exec")
    return output
