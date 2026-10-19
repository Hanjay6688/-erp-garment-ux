from types import SimpleNamespace
import native_probe_v2 as retained
r=retained.runner
r.cases=SimpleNamespace(EXPECTED=len(retained.IDS),cases=retained.cases)
r.verify=retained.cp17_runner.verify
r.OUT=r.bundle.ROOT/'cp6-proof/t3/ASTRA_R3_RETAINED_NATIVE.json'
r.package._writer_runtime=lambda browser_mode=False:r.run()
r.package.run('install')
