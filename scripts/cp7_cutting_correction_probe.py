"""Source-bound cutting reopen Native19; full original install/restore gates."""
import cp7_f05_analysis_probe as probe
import cp6_t3_package_run as package
if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:probe.run(cutting_correction=True)
    package.run('install')
