"""K2 retention: staged results kept 7 days after they finished, then expired; the private purge rule, on the closed Native analysis harness."""
import cp7_f05_analysis_probe as probe
if __name__=='__main__':
 probe.package._writer_runtime=lambda browser_mode=False:probe.run(k2_retention=True)
 probe.package.run('install')
