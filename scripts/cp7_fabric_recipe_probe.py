"""Reuse the closed Native analysis harness; retain all mandatory boundaries."""
import cp7_f05_analysis_probe as probe
if __name__=='__main__':
 probe.package._writer_runtime=lambda browser_mode=False:probe.run(fabric_recipe=True)
 probe.package.run('install')
