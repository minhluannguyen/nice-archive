### 2026-07-31: Kernel batch 2 standby blocked on missing research handoffs
**By:** Architect
**What:** I checked `.squad/decisions/inbox/` for Batch 2 research handoffs for CVE-2021-4034, CVE-2022-0847, and CVE-2016-5195. No matching `research-handoff-cve-{id}*` documents are present, so I did not create new case skeletons. I also confirmed that all three CVEs already have existing case directories under `cves/`.
**Why:** Creating duplicate case directories before research arrives would conflict with the requested workflow and with the repository’s current state. If new research lands later, it should likely be treated as remediation or restructuring work against the existing cases rather than brand-new case creation.
