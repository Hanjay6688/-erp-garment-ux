"""Isolated Native ordinary supplier payment correction qualification."""
import cp7_f05_analysis_probe as probe
if __name__=='__main__':
    probe.package._writer_runtime=lambda browser_mode=False:probe.run(supplier_payment_correction=True)
    probe.package.run('install')
