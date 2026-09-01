# CP3 Attendance HPP — Source Candidate Review Boundary

Status: SOURCE-ONLY CANDIDATE; DO NOT APPLY, MERGE, OR DEPLOY.

- Base `main`: `bf3ce8e2821f120d8abd8788daf07f6da7c15459`
- Writer: Chat Sol Pro
- Reviewer: Work Sol Max
- ERP Enteng UAT mutation: none
- ERP-Garment legacy mutation: none
- Auth/Storage/cron/Cloudflare mutation: none
- Denominator contract: immutable explicit `SELESAI_DIJAHIT`, never QC GOOD/FG/laundry/rework/Susulan.
- Eligibility: explicit `MANDOR` + `attendance_required=true` + explicit `is_special=false`.
- Candidate remains no-hook/no-browser-grant/no-service-role-grant until independent delta audit and local behavior/concurrency evidence pass.

This file is an interim review marker. It is superseded by the final machine-readable candidate manifest after CI evidence is reconciled.
