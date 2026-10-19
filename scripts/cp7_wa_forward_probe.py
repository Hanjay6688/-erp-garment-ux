"""WA (owner D17-3..D17-6): Pengingat sistem and their forwarding to the owner's WhatsApp through CallMeBot, tested on the closed Native analysis harness against the fake CallMeBot only (no real message, no real key)."""
import cp7_f05_analysis_probe as probe
if __name__=='__main__':
 probe.package._writer_runtime=lambda browser_mode=False:probe.run(wa_forward=True)
 probe.package.run('install')
