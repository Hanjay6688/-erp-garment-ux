"""Install/qualify on a disposable accepted CP6 clone; never hosted install."""
import cp7_f05_analysis_probe as base
if __name__=='__main__':
 base.package._writer_runtime=lambda browser_mode=False:base.run(attention=True)
 base.package.run('install')
