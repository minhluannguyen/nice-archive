### 2026-07-31: Architect-4 Remediation — Curl + Zlib

**Owner:** Architect-4
**Requested by:** @zimmi48
**Re:** Reviewer-2 rejection (reviewer-gate-batch1-part2.md)

**Environment blocker (VERIFY-1 persists):** The interactive shell/`nix`/`gcc`
were unavailable this session — every `bash` invocation returned
"Failed to start bash process" (same failure Reviewer-2 hit). All work below is
implemented correct-by-construction from authoritative sources; the four sha256
pins and the runtime 400/200 and 134/0 outcomes still require one `nix`-capable
follow-up run before final merge.

**CVE-2022-35252 (Curl):**
- CURL-1 remediated: real machine-checkable assertion block implemented.
  - Variant marker: `/etc/nice-archive/cve-2022-35252-variant` (build-time, environment.etc).
  - curl-version marker: `/etc/nice-archive/cve-2022-35252-curl-version`.
  - Status marker: `/etc/nice-archive/cve-2022-35252-http-status`, written by the
    new `cve-2022-35252-trigger` (curl `-o /dev/null -w '%{http_code}'` on /fetch2).
  - test.py: reads variant marker, runs trigger, asserts the status marker via the
    framework assertion block `ab.check_file_contains(client, status_file, "400"|"200")`
    — 400 on vulnerable, 200 on fixed. No more TODO / no-op.
  - `ab.check_http_status` intentionally NOT added; asserted inline via
    `check_file_contains` (jq-case pattern), per Reviewer option 2.
- DOC-1 remediated: readme.md rewritten, production-ready; skeleton/TODO wording
  removed; CWE corrected to CWE-1286; oracle table (400/200) documented; pins +
  verification note reconciled with the validator pin doc.
- Files updated: `test.py`, `vm-client.nix`, `readme.md`.
- Status: **READY FOR REVIEWER-3 RE-GATE** (pending sha256/runtime confirmation).

**CVE-2018-25032 (Zlib):**
- ZLIB-1 remediated: placeholder removed. Root cause and trigger sourced from the
  upstream fix commit `madler/zlib@5c44459c3b28a9bd3283aaceab7c615f8020c531`, zlib
  issue #605, and Tavis Ormandy's oss-security post (2022-03-24). The commit
  message defines the exact trigger (Z_FIXED forcing fixed codes; near-maximal
  31-bit length/distance pairs overrun the symbol table that pending_buf overlays;
  smallest margin at low memLevel). Rather than a fragile opaque blob, the PoC is a
  self-contained, deterministic harness (`exploit/zlib_deflate_poc.c`) that builds
  the pathological input in-memory (fixed-seed LCG; back-to-back ~32 KB copies →
  ~32000-distance max-range matches; 1-byte break every ~200 bytes → length codes
  in 131..257 = 5 extra bits). `exploit/crafted_input.bin` de-placeholdered
  (now documents origin; unreferenced, can be `git rm`-ed).
  - Evidence: https://github.com/madler/zlib/commit/5c44459c3b28a9bd3283aaceab7c615f8020c531 ,
    https://github.com/madler/zlib/issues/605 ,
    https://www.openwall.com/lists/oss-security/2022/03/24/1
- ZLIB-2 remediated: weak `!= 0` oracle replaced. Harness turns both failure modes
  (OOB heap corruption → glibc abort at deflateEnd; or silent corrupted stream →
  detected round-trip mismatch → abort()) into SIGABRT. test.py asserts exit
  code 134 with `ab.check_core_dump_exists(expected_signal="ABRT")` fallback, and
  exit 0 on fixed — mirroring the approved CVE-2023-50246 jq test.
- ZLIB-3 remediated: all Nix `${...}` interpolation removed from test.py. The
  trigger binary + generated input are provided entirely by `vm-server.nix`
  (runCommandCC + writeShellScriptBin on PATH); test.py just runs
  `cve-2018-25032-trigger`. (Stored a repo memory documenting the readFile/no-interp rule.)
- ZLIB-4 remediated: harness no longer uses `compress2` (memLevel=8). It uses
  `deflateInit2(strm, Z_BEST_COMPRESSION, Z_DEFLATED, windowBits=15, memLevel=1,
  Z_FIXED)` — the documented vulnerable path — plus the crafted input.
- DOC-1 remediated: readme.md rewritten; skeleton/TODO removed; root cause
  corrected (it is the pending_buf/sym-table overlay under Z_FIXED, not
  `deflate_stored()`); affected range 1.2.2.2–1.2.11; pins + verification note.
- Files updated: `exploit/zlib_deflate_poc.c` (new), `exploit/crafted_input.bin`
  (de-placeholdered), `test.py`, `vm-server.nix`, `readme.md`.
- Status: **READY FOR REVIEWER-3 RE-GATE** (pending sha256/runtime confirmation).

**Blockers:** All hard blockers (CURL-1, ZLIB-1..4, DOC-1) remediated in code and
docs. VERIFY-1 remains an OPEN RISK, not a code gap: no `nix`/shell this session, so
(a) the four sha256 pins and (b) the observed 400/200 and 134/0 outcomes are not
runtime-confirmed. Reviewer-3 or a validator with a working `nix` must run:
  - `nice-archive test --case cve-2022-35252-curl-cookie-poisoning --vulnerable true|false`
  - `nice-archive test --case cve-2018-25032-zlib-deflate-overflow --vulnerable true|false`
  - `git add` both case dirs first (flake sees only git-tracked files; the new
    `zlib_deflate_poc.c` must be staged).

**Residual note for zlib:** the differential is designed to be robust (crash OR
detected round-trip corruption both abort), but the exact triggering input for the
overlay overrun could not be executed here; if 1.2.11 does not abort on the first
config, the harness already sweeps four configs — a validator should confirm at
least one aborts on 1.2.11 and none abort on 1.2.12.

**Next:** Await Reviewer-3 re-gate + a nix-capable confirmation pass, then Batch 1 commit.
