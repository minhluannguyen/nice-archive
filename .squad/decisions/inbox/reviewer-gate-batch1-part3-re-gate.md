### 2026-07-31: Reviewer Gate — Batch 1 Part 3 (Curl + Zlib Re-Gate)
**By:** Reviewer-3
**Verdict:** REJECT

**Precondition failure — remediation not found:**
- The expected handoff `.squad/decisions/inbox/architect-remediation-curl-zlib.md` **does not exist**.
- No remediation was applied to either case. Both case directories are byte-for-byte identical to
  the state Reviewer-2 rejected in `reviewer-gate-batch1-part2.md`.
- Repo-wide grep confirms none of the remediation artifacts exist:
  - `check_http_status`, `http-status`, `35252-variant` → **No matches found**
  - `deflateInit2`, `memLevel` → **No matches found**
- Note: `bash`/`nix` were unavailable this session (bash process failed to start), so pins could
  not be independently verified — but every blocker below was re-checked via static file inspection,
  which is sufficient to establish that no remediation occurred.

---

**Curl (CVE-2022-35252):**
- CURL-1 (oracle): **FAIL** — `test.py` still contains `# TODO: Implement HTTP status code checking`,
  still only sets a `variant` string and prints (lines 33–45). No `ab.check_*` assertion block; the
  script can never fail. `vm-client.nix` writes **no** `/etc/nice-archive/cve-2022-35252-variant`
  marker and **no** `...-http-status` marker (it only installs curl + procps). All 4 required checks
  are false.
- DOC-1 (docs): **FAIL** — `readme.md` still ends with `**Status**: Skeleton implementation (Phase 3)`
  (line 76) and `**Next**: Validator to find exact curl version pins` (line 77). "Known Issues"
  still says `Nixpkgs commits: TODO ... Using placeholder for fixed version (needs verification)`
  (lines 70–72). No skeleton/TODO wording was removed.
- VERIFY-1 (sha256 flag): **FLAG** — URLs are valid GitHub/nixpkgs archive links and sha256 values
  are present for both variants, but not independently verifiable this session (no working nix/bash),
  and `readme.md` still labels the fixed pin a placeholder, contradicting the validator pin doc.
- Status: **REJECTED** — oracle is still a no-op; docs still skeleton. Unchanged from Part 2.

**Zlib (CVE-2018-25032):**
- ZLIB-1 (PoC): **FAIL** — `exploit/crafted_input.bin` still contains the literal text
  "This is a placeholder file. Replace with binary PoC input." plus the `TODO: Validator to replace`
  block. It is still a text file, not a binary PoC, and there is no evidence of sourcing from
  NVD / zlib issue #605 / upstream.
- ZLIB-2 (oracle): **FAIL** — vulnerable branch still uses `assert result[0] != 0` (line 26). It was
  not tightened to `== 134`. (`ab.check_core_dump_exists(expected_signal="ABRT")` is present on
  line 28, but it runs after a weak `!= 0` gate and against a non-functional trigger, so the oracle
  is still false-positive-prone.)
- ZLIB-3 (Nix interpolation): **FAIL** — `test.py` still embeds `${pkgs.util-linux}/bin/setsid` and
  `< ${./exploit/crafted_input.bin}` inline (lines 17, 34). `test.py` is read verbatim via
  `builtins.readFile`, so these `${...}` are literal shell text and will error at runtime.
- ZLIB-4 (harness): **FAIL** — the C harness in `vm-server.nix` still calls `compress2(out, &outlen,
  in, inlen, 9)` (line 49) with default memLevel. No `deflateInit2`, no memLevel=1, no window/mem
  tuning. Cannot reach the vulnerable `deflate_stored`/sym-buffer path.
- DOC-1 (docs): **FAIL** — `readme.md` still ends with `**Status**: Skeleton implementation (Phase 3)`
  (line 74) and "Known Issues" still lists `Nixpkgs commits: TODO` and
  `PoC input: TODO - Replace placeholder crafted_input.bin` (lines 67–70).
- VERIFY-1 (sha256 flag): **FLAG** — URLs valid and sha256 present for both variants, but not
  independently verified this session, and readme still labels them placeholders.
- Status: **REJECTED** — placeholder exploit, weak/false-positive oracle, live Nix interpolation
  bug, wrong harness, skeleton docs. Unchanged from Part 2.

**Blockers (if any):**
- REMEDIATION-MISSING (hard, both): No remediation was performed. The handoff doc
  `architect-remediation-curl-zlib.md` is absent and no case files changed since the Part 2
  rejection. All 7 original blockers remain OPEN:
  - CURL-1 (oracle: no assertion / no variant marker / no http-status marker) — still open
  - ZLIB-1 (placeholder PoC text file) — still open
  - ZLIB-2 (weak `!= 0` oracle) — still open
  - ZLIB-3 (literal `${...}` interpolation in test.py) — still open
  - ZLIB-4 (compress2 defaults cannot reach vulnerable path) — still open
  - DOC-1 (both readmes still "Skeleton implementation (Phase 3)" + TODO pins) — still open
  - VERIFY-1 (sha256 not independently confirmed; readmes still call pins placeholders) — still flagged
- Additional: `ab.check_http_status` still does not exist in `src/assertion_blocks/blocks.py`
  (available checks unchanged: service_log_contains, root_gid, screen_text, file_exists,
  file_contains, file_size_equals, cpu_usage_high, memory_usage_high, exact_execution_time,
  core_dump_exists). Curl oracle must either add this helper or assert status inline.

**Next:** NOT ready for Batch 1 commit. Re-gate reported no delivered remediation — this is a
process gap, not a subtle quality miss. Route back to Architect-4 to actually perform and hand off
the Part 2 remediation (real zlib PoC + tightened `==134` oracle + de-interpolated test.py + fixed
`deflateInit2` harness + curl assertion & variant/http-status markers + both readmes finalized),
then re-submit for gate. A follow-up run with a working `nix`/shell should independently confirm the
four sha256 pins before merge.
