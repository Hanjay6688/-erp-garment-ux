"""No monkeypatch: candidate stop-aware helper must accept the declared G01 stop."""
import sys
from pathlib import Path
import cp6_t3_aligned_chain as aligned
import cp6_g01_baseline as g01
if __name__=='__main__':raise SystemExit(aligned.run(Path('../auditor/cp6-proof/t3/ALIGNED_CHAIN.json'),stop=g01.STOP))
