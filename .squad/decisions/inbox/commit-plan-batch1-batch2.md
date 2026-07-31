# Commit Plan — CVE-2023-50246 & Batch 1 Completion

**Date**: 2026-07-31T20:20+02:00  
**Status**: Ready to execute once agents complete

## Commit 1: CVE-2023-50246 (jq)

**Stage**: Ready now (Reviewer approved)

**Message**:
```
CVE-2023-50246: Add jq heap buffer overflow reproducible case

- CVE: CVE-2023-50246 (jq 1.7 decNumber off-by-one buffer overflow)
- Affected: jq 1.7, 1.7-rc1, 1.7-rc2
- Fixed: jq 1.7.1
- Root cause: Off-by-one buffer allocation in decToString() with large negative exponents
- Vulnerability: Heap buffer overflow causes SIGABRT (exit code 134)

Implementation:
- flake.nix: Parameterized nixpkgs pins for vulnerable/fixed variants
- vm-server.nix: NixOS test VM with jq 1.7 or 1.7.1
- test.py: Automated test with exit code 134 oracle + ABRT core dump fallback
- readme.md: Complete CVE documentation

Nixpkgs pinning:
- Vulnerable: commit 4b0751b (jq 1.7)
- Fixed: commit f45e75f (jq 1.7.1)
- Verified against existing jq cases (cve-2023-50268, cve-2024-23337, cve-2024-53427)

Test oracle:
- Vulnerable: Input '-10E-1000000001' → exit code 134 (SIGABRT)
- Fixed: Input '-10E-1000000001' → exit code 0

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```

**Files to add**:
```
cves/cve-2023-50246-jq-heap-buffer-overflow/
  ├── flake.nix
  ├── vm-server.nix
  ├── test.py
  ├── readme.md
  ├── exploit/
  ├── flake.lock
  └── __pycache__/
```

## Commits 2-4: Batch 1 (curl, vim, zlib)

**Stage**: Pending (awaiting Validator-3 nixpkgs pins)

**Timeline**:
1. Validator-3 completes → produces 3 handoffs with final pins + sha256 hashes
2. Validator-3 updates vm-server.nix files with hashes
3. Coordinator creates 3 commits (one per CVE)

**Message template**:
```
CVE-YYYY-NNNN: Add [product] [vulnerability type] reproducible case

- CVE: CVE-YYYY-NNNN
- Product: [product]
- Affected: [versions]
- Fixed: [version]
- Root cause: [brief description]
- Vulnerability: [type + impact]

Implementation:
- flake.nix: Parameterized for vulnerable/fixed
- vm-server.nix: Test VM setup with trigger
- test.py: Automated oracle assertions
- readme.md: CVE facts + PoC

Nixpkgs pinning:
- Vulnerable: commit XXXXX (sha256: ...)
- Fixed: commit YYYYY (sha256: ...)

Test oracle:
- Vulnerable: [oracle check]
- Fixed: [oracle check]

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```

## Commits 5-7: Batch 2 (PwnKit, Dirty Pipe, Dirty CoW)

**Stage**: Pending (awaiting Researcher-3 research + Architect-2 design)

**Timeline**:
1. Researcher-3 produces 3 research handoffs
2. Architect-2 designs 3 cases
3. Validator tests all 3
4. Coordinator creates 3 commits

---

## Execution Order

1. ✅ Commit 1 (jq): Execute immediately once agents start
2. ⏳ Commits 2-4 (curl, vim, zlib): After Validator-3 completes
3. ⏳ Commits 5-7 (PwnKit, Dirty Pipe, Dirty CoW): After full design/test cycle

## Total Expected Commits

**6-7 commits** (1 jq approved, 3 Batch 1 pending pins, 3 Batch 2 pending research/design)

---

**Prepared by**: Coordinator  
**Waiting for**: Validator-3, Researcher-3, Architect-2 completion
