"""Explicit fabric-rule Native113; every retained WA99 control remains mandatory."""
import cp7_b_f05_analysis_probe as probe
if __name__ == '__main__':
    probe.package._writer_runtime = lambda browser_mode=False: probe.run(wa_forward=True, ow14b_rules=True)
    probe.package.run('install')
