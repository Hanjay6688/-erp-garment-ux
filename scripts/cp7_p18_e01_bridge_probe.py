"""Focused E01 consumer bridge on the exact complete Native284 product stack.

Seven predeclared executions do not replace Native284 or full P18/P19 exits.
All install, restore, primary, backup, advisor and Auth cleanup gates remain.
"""
import cp7_f05_analysis_probe as probe

if __name__ == '__main__':
    probe.package._writer_runtime = lambda browser_mode=False: probe.run(p18_e01=True)
    probe.package.run('install')
