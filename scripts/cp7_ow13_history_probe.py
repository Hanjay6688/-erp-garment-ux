"""OW13b on the closed Native analysis harness; retained real-user controls."""
import cp7_b_f05_analysis_probe as probe

if __name__ == '__main__':
    probe.package._writer_runtime = lambda browser_mode=False: probe.run(
        pl5_history_yield=True, ow13_complete_history=True)
    probe.package.run('install')
