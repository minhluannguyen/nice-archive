### 2026-07-31: Reviewer Gate — Batch 1 Part 2 (Curl + Zlib)
**By:** Reviewer-2
**Verdict:** REJECT

Both cases fail the same quality bar that rejected CVE-2023-50246: skeleton/Phase-3
documentation with TODO pins, and oracles that are not real machine-checkable checks
(no assertion at all for curl; a placeholder PoC + `!= 0` weak assertion for zlib).

---

**Curl (CVE-2022-35252):**
- Oracle: **FAIL**
  - `test.py` contains `# TODO: Implement HTTP status code checking` and has **no assertion whatsoever**.
    It only sets a `variant` string and prints; the script can never fail, so it always "passes"
    for both vulnerable and fixed builds. This is not a machine-checkable oracle.
  - The mandatory assertion block is absent.
  - Design specified `ab.check_http_status(...)`, but that helper **does not exist** in
    `src/assertion_blocks/blocks.py` (available: check_service_log_contains, check_root_gid,
    check_screen_text, check_file_exists, check_file_contains, check_file_size_equals,
    check_cpu_usage_high, check_memory_usage_high, check_exact_execution_time, check_core_dump_exists).
  - `vm-client.nix` writes no `/etc/nice-archive/...-variant` marker, so the test has no ground
    truth to compare the observed HTTP status against.
- Pins: **PARTIAL (flagged)** — `vm-client.nix` has URL + sha256 for both variants; vulnerable =
  curl 7.84.0 (< 7.85.0, valid), fixed = 7.85.0 (valid). But `readme.md` still says
  "Nixpkgs commits: TODO ... Using placeholder for fixed version (needs verification)",
  contradicting the validator pin doc. sha256 could not be independently confirmed this session
  (see Blockers).
- VM: **PARTIAL** — server=invariant, client=package structurally correct, but no variant marker
  emitted and the test cannot assert against it.
- Docs: **FAIL** — `readme.md` ends with `**Status**: Skeleton implementation (Phase 3)` and
  `**Next**: Validator to find exact curl version pins`, plus a "Known Issues: TODO" pin section.
  Identical skeleton wording to the prior CVE-2023-50246 rejection.
- Status: **REJECTED** — oracle is a no-op (TODO, no assertion) and docs are non-commit-ready.

**Zlib (CVE-2018-25032):**
- Oracle: **FAIL**
  - `exploit/crafted_input.bin` is a **text placeholder**, not a PoC. It literally contains
    "This is a placeholder file. Replace with binary PoC input." and "TODO: Validator to replace
    this". The trigger input does not exist.
  - Vulnerable branch uses `assert result[0] != 0` — accepts **any** non-zero exit. This is the
    exact weak oracle that got CVE-2023-50246 rejected; it must enforce the crash condition
    (exit 134 / SIGABRT), like the approved jq case does.
  - `test.py` embeds `${pkgs.util-linux}/bin/setsid` and `< ${./exploit/crafted_input.bin}`, but
    `test.py` is loaded via `builtins.readFile` with **no Nix interpolation**
    (`src/test-configs/test-template.nix:128`). Those `${...}` are literal shell text and will
    error ("bad substitution" / bogus path), so the command fails for the wrong reason and the
    `!= 0` assertion passes falsely.
  - Harness uses `compress2()` with default memLevel(8). CVE-2018-25032 requires `deflateInit2`
    with memLevel=1 (specific window/mem settings) plus the known crafted input to reach the
    vulnerable `deflate_stored`/symbol-buffer path; this harness cannot reproduce the overflow
    even once a real PoC is supplied.
- Pins: **PARTIAL (flagged)** — `vm-server.nix` has URL + sha256 for both; vulnerable = zlib 1.2.11,
  fixed = 1.2.12 (correct version boundary for the CVE). But `readme.md` says commits/PoC are
  "TODO/placeholder", contradicting the validator pin doc. sha256 not independently confirmed
  this session.
- VM: **PARTIAL** — single-VM package variant is structurally fine and emits variant + zlib-version
  marker files (good), but the trigger + input are non-functional as above.
- Docs: **FAIL** — `readme.md` ends with `**Status**: Skeleton implementation (Phase 3)` and lists
  "Nixpkgs commits: TODO" and "PoC input: TODO - Replace placeholder crafted_input.bin".
- Status: **REJECTED** — placeholder exploit, weak/false-positive oracle, and skeleton docs.

**Blockers (if any):**
- ZLIB-1 (hard): `exploit/crafted_input.bin` is a placeholder text file — no working PoC. Source
  the real input (zlib issue #605 / CVE-2018-25032) and confirm it crashes 1.2.11 and not 1.2.12.
- ZLIB-2 (hard): Weaken oracle `assert result[0] != 0` → enforce exit code 134 with a
  `ab.check_core_dump_exists(expected_signal="ABRT")` fallback, mirroring the approved
  CVE-2023-50246 test.py.
- ZLIB-3 (hard): Remove Nix `${...}` interpolation from `test.py` (it is read verbatim). Reference
  the trigger binary and input via the derivation/PATH instead, as the jq cases do.
- ZLIB-4 (hard): Fix the C harness to use `deflateInit2` with the PoC's memLevel/windowBits;
  `compress2` defaults cannot reach the vulnerable path.
- CURL-1 (hard): `test.py` has no assertion (TODO). Add a real oracle that reads a variant marker
  and asserts exact HTTP status: 400 on vulnerable, 200 on fixed. Emit the variant marker from
  `vm-client.nix` and add the mandatory assertion block. `ab.check_http_status` does not exist —
  either add it to the library or assert the status inline.
- DOC-1 (hard, both): `readme.md` files still say "Skeleton implementation (Phase 3)" with TODO
  pin sections — not commit-ready. Finalize CVE facts, confirmed pins, PoC, and expected behavior.
- VERIFY-1 (flag, not auto-reject — coordinator decision): sha256 pins could **not** be
  independently confirmed. The validator noted "Public-source corroboration only; nix-prefetch
  could not run", and this review session's shell/`nix` was unavailable (bash process failed to
  start), so I have no runtime evidence that either tarball hash resolves. Per gate rules this is
  documented as a risk, not an auto-reject; the pins themselves (versions, URLs, sha256 presence)
  are structurally correct. Both `readme.md` files also still label the pins as placeholders,
  which must be reconciled with the validator doc before merge.

**Next:** NOT ready for Batch 1 commit. Both cases return for remediation (Architect recommended
as owner, per the CVE-2023-50246 precedent, since blockers span exploit, oracle, and docs). Re-gate
after: real zlib PoC + tightened oracle + de-interpolated test.py + curl assertion added + both
readmes finalized. A follow-up run with a working `nix`/shell should independently confirm the four
sha256 pins before merge.
