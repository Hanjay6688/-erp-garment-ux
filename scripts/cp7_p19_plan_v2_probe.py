"""P19 plan v2: a production plan from a staged snapshot, rechecked live when applied, on the closed Native analysis harness."""
import cp7_f05_analysis_probe as probe
if __name__=='__main__':
 probe.package._writer_runtime=lambda browser_mode=False:probe.run(p19_plan_v2=True)
 probe.package.run('install')
