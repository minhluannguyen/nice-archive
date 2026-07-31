# Commit Strategy — Batch 1 Final (Updated 2026-07-31T20:45Z)

**By:** Coordinator  
**Status:** Production Mode Execution Plan

## Case Status Matrix

| CVE | Status | Approved? | Pins | Validator Note | Action |
|-----|--------|-----------|------|-----------------|--------|
| CVE-2023-50246 (jq) | ✅ COMPLETE | YES | ✅ Verified | Ready | **COMMIT NOW** |
| CVE-2022-35252 (curl) | ⏳ GATING | Pending | ✅ Updated | Pins from public corroboration | Await Reviewer-2 |
| CVE-2019-12735 (vim) | ⚠️ BLOCKED | No | ❌ Missing | No shell → cannot find 8.1.1364/1365 revisions | **Escalate** (see below) |
| CVE-2018-25032 (zlib) | ⏳ GATING | Pending | ✅ Updated | Pins from public corroboration | Await Reviewer-2 |

## Approved Cases — Ready for Merge

### CVE-2023-50246 (jq Heap Buffer Overflow)
- **Status:** ✅ APPROVED by Reviewer (re-gate completed)
- **Directory:** `cves/cve-2023-50246-jq-heap-buffer-overflow/`
- **Files ready:** flake.nix, vm-server.nix, test.py, readme.md, exploit/
- **Commit message:**
  ```
  Add CVE-2023-50246: jq 1.7 heap buffer overflow (closes #X)
  
  - Vulnerable: jq 1.7 (commit 4b0751b)
  - Fixed: jq 1.7.1 (commit f45e75f)
  - Oracle: Vulnerable variant exits with code 134 (ABRT)
  - Test: Automated input PoC via test.py
  
  Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
  ```

## Pending Cases — Awaiting Reviewer-2 Gate

### CVE-2022-35252 (curl Cookie Poisoning)
- **Status:** ⏳ Validator-3 updated pins; Reviewer-2 gating now
- **Validator findings:** Pins corroborated from public sources; local nix-prefetch-url unavailable
- **Next:** Reviewer-2 approval → commit

### CVE-2018-25032 (zlib Deflate Overflow)
- **Status:** ⏳ Validator-3 updated pins; Reviewer-2 gating now
- **Validator findings:** Pins corroborated from public sources; local nix-prefetch-url unavailable
- **Next:** Reviewer-2 approval → commit

## Blocked Cases — Action Required

### CVE-2019-12735 (vim Modeline RCE)
- **Status:** ❌ BLOCKED on nixpkgs revision discovery
- **Problem:** Validator-3 could not locate nixpkgs commits for vim 8.1.1364 or 8.1.1365
  - Shell/bash unavailable → cannot run nix-prefetch-url
  - NixHub package index does not expose these vim versions
  - Web searches returned non-existent GitHub commit URLs
- **Current:** vm-server.nix NOT updated; test.py oracle ready but cannot validate
- **Escalation path:**
  1. **Option A:** Coordinator attempts git clone of nixpkgs, grep for vim 8.1.1364 in history
  2. **Option B:** Use Validator-4 with upgraded model (Claude Opus 4.8) to perform deep nixpkgs archaeology
  3. **Option C:** Delay vim case to Batch 3; proceed with jq/curl/zlib now
- **Recommendation:** Option B (upgrade model for deeper search) or Option C (defer vim)

## Commit Execution Order

**Phase 1 (NOW):**
1. Commit CVE-2023-50246 (jq) — APPROVED ✅

**Phase 2 (Await Reviewer-2 completion):**
2. If Reviewer-2 APPROVES curl: Commit CVE-2022-35252 (curl)
3. If Reviewer-2 APPROVES zlib: Commit CVE-2018-25032 (zlib)

**Phase 3 (Resolve vim blocker):**
4. Proceed with vim case OR defer to Batch 3

## Git Commands (when bash becomes available)

```bash
# Phase 1: Commit jq
git add cves/cve-2023-50246-jq-heap-buffer-overflow/
git commit -m "Add CVE-2023-50246: jq 1.7 heap buffer overflow" \
  --trailer="Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"

# Phase 2: Commit curl (if approved)
git add cves/cve-2022-35252-curl-cookie-poisoning/
git commit -m "Add CVE-2022-35252: curl 7.84.0 cookie poisoning" \
  --trailer="Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"

# Phase 2: Commit zlib (if approved)
git add cves/cve-2018-25032-zlib-deflate-overflow/
git commit -m "Add CVE-2018-25032: zlib 1.2.11 deflate overflow" \
  --trailer="Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"

# Phase 3: Commit vim (if resolved) OR skip to Batch 2
git add cves/cve-2019-12735-vim-modeline-rce/
git commit -m "Add CVE-2019-12735: vim 8.1 modeline RCE" \
  --trailer="Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Batch 2 Status

- **Research:** ✅ Researcher-3 completed (PwnKit, Dirty Pipe, Dirty CoW handoffs ready)
- **Design:** ⏳ Architect-3 inspecting existing case directories
- **Next:** Architect-3 approval → Validator-4 tests → Reviewer-3 gates → Batch 2 commits
