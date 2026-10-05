"""Reuse the closed Native analysis harness with the complete reminder stack."""
import cp7_f05_analysis_probe as probe
if __name__=='__main__':
 probe.package._writer_runtime=lambda browser_mode=False:probe.run(fabric_reminder=True)
 probe.package.run('install')
