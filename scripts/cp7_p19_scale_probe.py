"""P19 full-application Native scale ladder (100/300/1000/5000 targets); measurement only, no limit raised."""
import cp7_f05_analysis_probe as probe
if __name__=='__main__':
 probe.package._writer_runtime=lambda browser_mode=False:probe.run(p19_scale=True)
 probe.package.run('install')
