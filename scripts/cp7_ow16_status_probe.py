"""OW16 isolated Native/real-user qualification over the closed analysis stack."""
import cp7_b_f05_analysis_probe as probe

if __name__ == '__main__':
    probe.package._writer_runtime = lambda browser_mode=False: probe.run(pl5_history_yield=True, ow16_status=True)
    probe.package.run('install')
