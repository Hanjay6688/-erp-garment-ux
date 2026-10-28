# Historical qualification workflow isolation

The 24 historical GitHub entry points are retired on this candidate. Their complete
original bytes remain in frozen-workflows/*.yml.txt and in the pinned ancestor Git
commit. Every original frozen SOURCE manifest is unchanged. The materializer verifies
the archive against both Git and each frozen manifest, refuses tracked historical
workflow entries and mismatched existing files, then recreates exact read-only proof
inputs only inside a checked-out workspace. GitHub cannot dispatch files created
locally after checkout. Existing SQL, JavaScript, B tooling and case bodies are unchanged.

The source-check job materializes those inputs. The separate CodeQL job checks a fresh
checkout of the candidate, with security-extended and the original zero-findings gate;
no query is disabled and no path exclusion or suppression is added. This is a new A
qualification, not acceptance of the old b87 scan or the B filesystem-race finding.

Future composed qualification entry points must invoke this explicit materialization
before reading historical proof paths. The currently running DF and closed UI8dd
candidates remain unchanged. No default/official/hosted adoption follows this preparation.
