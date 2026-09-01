# CP3 source archive V2

This branch contains a hash-bound source-only reconstruction of the Attendance HPP route from clean `main` `bf3ce8e…`.

The committed archive materializes readable SQL and test tooling for an immutable `SELESAI_DIJAHIT` denominator. It is intentionally **not** an ERP Enteng UAT apply, Auth change, Cloudflare deploy, or production connection. The workflow restores the exact CP2 encrypted baseline into disposable local Supabase, runs rollback acceptance and real two-session races, then destroys plaintext/local state.

A green run means only `READY_FOR_WORK_SOL_MAX_DELTA_REAUDIT_NOT_READY_FOR_UAT_APPLY`.
