"""P19 staged analysis (5,000 targets as supported capacity) on the closed Native analysis harness."""
import cp7_f05_analysis_probe as probe
if __name__=='__main__':
 probe.package._writer_runtime=lambda browser_mode=False:probe.run(p19_staged=True)
 probe.package.run('install')
