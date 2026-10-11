"""K6: the PL-8 exhaustion proofs are made by the server (pg_cron runner, one window per tick through the unchanged prover); tested with the real pg_cron on the disposable copy, on the closed Native analysis harness."""
import cp7_f05_analysis_probe as probe
if __name__=='__main__':
 probe.package._writer_runtime=lambda browser_mode=False:probe.run(k6_proof_runner=True)
 probe.package.run('install')
