"""K4: the staged analysis runs on the server (pg_cron runner, one unit per tick through the page's own step), so it goes on while its page is closed; tested with the real pg_cron on the disposable copy, on the closed Native analysis harness."""
import cp7_f05_analysis_probe as probe
if __name__=='__main__':
 probe.package._writer_runtime=lambda browser_mode=False:probe.run(k4_runner=True)
 probe.package.run('install')
