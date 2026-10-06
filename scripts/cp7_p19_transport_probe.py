"""P19 analysis job/segment transport on the closed Native analysis harness."""
import cp7_f05_analysis_probe as probe
if __name__=='__main__':
 probe.package._writer_runtime=lambda browser_mode=False:probe.run(p19_transport=True)
 probe.package.run('install')
