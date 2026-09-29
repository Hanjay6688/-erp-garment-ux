"""P13 reviewed native close/reopen plus original dated-report regression."""
import cp7_p13_finance_probe as finance
if __name__=='__main__':
 finance.package._writer_runtime=lambda browser_mode=False:finance.run(include_period=True)
 finance.package.run('install')
