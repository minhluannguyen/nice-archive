### 2026-07-31: Final Reviewer Gate — Curl + Zlib
**By:** Reviewer-Final
**Verdict:** APPROVE

**Environment:** `bash`/`nix` unavailable this session (every invocation returned
"Failed to start bash process"), so verification was static (view/grep). Runtime
outcomes remain under VERIFY-1 as designed.

---

**Curl (CVE-2022-35252): PASS**
1. ✅ `test.py` has a real, non-TODO assertion for HTTP status — reads the variant
   marker and asserts `ab.check_file_contains(client, status_file, "400")`
   (vulnerable) / `"200")` (fixed). No no-op path; unknown variant hard-asserts.
2. ✅ `vm-client.nix` emits `/etc/nice-archive/cve-2022-35252-http-status`. The new
   `cve-2022-35252-trigger` captures `curl -o /dev/null -w '%{http_code}'` on
   `/fetch2` and writes it: `printf '%s\n' "$code" > "$status_file"`. Variant +
   curl-version markers also emitted via `environment.etc`.
3. ✅ `readme.md` no longer says "Skeleton implementation" — rewritten, CWE-1286,
   oracle table (400/200), pins + reconciled verification note. No TODO pins.

**Zlib (CVE-2018-25032): PASS**
1. ✅ (in substance) Placeholder text is gone. Architect-4 replaced the opaque-blob
   strategy with a self-contained deterministic harness
   (`exploit/zlib_deflate_poc.c`) that builds the pathological input in-memory
   (fixed-seed LCG, Z_FIXED, near-maximal 31-bit length/distance pairs) — a valid,
   arguably superior reproduction for this parametric CVE (trigger = compression
   params + input shape, not a fixed blob). NOTE: `crafted_input.bin` itself is NOT
   a binary — it is now intentionally-unused documentation text explaining the
   origin; the harness does not read it. Recommend `git rm` it to avoid confusion.
   The underlying blocker (ZLIB-1: real working PoC present, placeholder removed) is
   resolved; the literal "is it a binary" wording is moot under the new design.
2. ✅ Handoff cites commit `5c44459c3b28a9bd3283aaceab7c615f8020c531`, issue #605,
   and Ormandy's 2022-03-24 oss-security post as evidence (readme + poc.c header).
3. ✅ `test.py` asserts `result[0] == 134` (SIGABRT), not `!= 0`.
4. ✅ `test.py` calls `ab.check_core_dump_exists(machine=server, expected_signal="ABRT")`
   as the fallback.
5. ✅ No `${...}` interpolation remains in `test.py`. The trigger binary + input are
   provided by `vm-server.nix` (`runCommandCC` + `writeShellScriptBin` on PATH);
   the only `${./exploit/...}` interpolation lives in `vm-server.nix`, where Nix
   interpolation is valid.
6. ✅ Harness uses `deflateInit2(&strm, Z_BEST_COMPRESSION, Z_DEFLATED, 15, 1, Z_FIXED)`
   — windowBits=15, **memLevel=1**, Z_FIXED — the documented vulnerable path.
7. ✅ `readme.md` no longer says "Skeleton implementation" — rewritten, CWE-787,
   1.2.2.2–1.2.11 range, root cause corrected to the pending_buf/sym-table overlay.

**Blockers:** None (all 7 original hard blockers — CURL-1, ZLIB-1..4, DOC-1 —
resolved).

**Open risks (non-blocking, VERIFY-1):** No `nix`/shell this or prior sessions, so
(a) the four sha256 pins, (b) the curl 400/200 and zlib 134/0 runtime outcomes, and
(c) confirmation that ≥1 zlib config aborts on 1.2.11 and none on 1.2.12, are not
runtime-confirmed. Per gate rules this is a documented risk, not an auto-reject.
Minor cleanup: `git rm cves/cve-2018-25032-zlib-deflate-overflow/exploit/crafted_input.bin`;
ensure `zlib_deflate_poc.c` is `git add`-ed (flake sees only tracked files).

**Next:** Ready for Batch 1 commit. A nix-capable follow-up must run
`nice-archive test` on both cases (`--vulnerable true|false`) and confirm the four
sha256 pins before final merge.
