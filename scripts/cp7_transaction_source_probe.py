"""Exact source navigation on the combined accepted F03/F05 stack."""
import cp7_f05_analysis_probe as probe
if __name__=='__main__':
 probe.package._writer_runtime=lambda browser_mode=False:probe.run(source_navigation=True)
 probe.package.run('install')
