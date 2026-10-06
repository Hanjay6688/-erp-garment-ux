"""Selected Native P19 load/recovery qualifier; no installed or full P19 exit."""
import cp7_f05_analysis_probe as probe

if __name__ == '__main__':
    probe.package._writer_runtime = lambda browser_mode=False: probe.run(p19_load=True)
    probe.package.run('install')
