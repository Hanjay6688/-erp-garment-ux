"""P19 Business Report v2: a report of a dated staged snapshot, actual finance and stock at the report date, on the closed Native analysis harness."""
import cp7_f05_analysis_probe as probe
if __name__=='__main__':
 probe.package._writer_runtime=lambda browser_mode=False:probe.run(p19_report_v2=True)
 probe.package.run('install')
