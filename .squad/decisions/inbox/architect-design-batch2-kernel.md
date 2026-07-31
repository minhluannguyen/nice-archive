### 2026-07-31: Architect Design — Batch 2 Kernel CVEs
**By:** Architect-3

**Scope:** Static design review of the 3 pre-existing kernel/privesc CVE cases
against Researcher-3's handoffs, the framework docs, and the canonical
`cve-2025-32463-chwoot` reference. Runtime `nix`/VM validation was NOT possible
in this environment (the bash/Nix backend refused to start on every attempt);
build-and-run verification is explicitly deferred to the Validator. No test
results are claimed as passing here.

**Framework convention confirmed (applies to all 3):**
- The same `test.py` is read (`builtins.readFile`) and executed for BOTH the
  vulnerable and fixed variants; the generator injects NO `variant` python
  variable (`src/test-configs/test-template.nix:128,141`).
- `ab.check_root_gid` uses `machine.succeed("su - <user> -c 'id'")`
  (`src/assertion_blocks/blocks.py:31-39`). If the user was never created, `su`
  fails, `succeed` raises, and the test fails.
- Therefore, like the flagship `chwoot` case, these privesc cases use the
  accepted "non-branching" pattern: `test-vulnerable-true` PASSES (proves the
  exploit crossed the privilege boundary) and `test-vulnerable-false` FAILS by
  design (exploit produced no UID/GID 0 account). Primary machine-checkable
  oracle = the vulnerable side, and it is solid.

---

**CVE-2021-4034 (PwnKit):**
- Research summary: polkit `pkexec` argv/envp OOB write via `argc==0`; affected
  upstream through polkit 0.119, fixed in 0.120 (handoff matches NVD/Qualys).
- Oracle type: privilege boundary — `ab.check_root_gid(server, "newuser")` after
  the gconv/`GCONV_PATH` PoC appends a UID/GID 0 line to `/etc/passwd`.
- VM structure: `flake.nix` → `oldKernelTestsGenerator`; vulnerable/fixed polkit
  are pinned via two `builtins.fetchTarball` nixpkgs revisions WITH sha256 in
  `vm-server.nix` (vuln `be1461fc…` sha256 `1fdlnfipa3q…`, fixed `2a51780f…`
  sha256 `1xzz2l9…`). Old kernel `linuxPackages_5_7` from nixpkgs `136a26be…`
  (nixos-20.09) — pins locked in `flake.lock`. Exploit built in-VM from vendored
  C (`exploit.c` + `evil-so.c`/`evil-so-root.c`); setuid `pkexec` provided via
  `security.wrappers`.
- Gaps found:
  1. (FIXED by me) `readme.md` documented a "Run a standalone VM"
     (`--name server-vulnerable`/`server-fixed`) section, but `flake.nix` never
     calls `standaloneVMGenerator`, so those outputs don't exist and the command
     would error. I replaced that section with accurate `pwnkit-exploit` usage.
  2. (Cosmetic) `environment.etc."pwnkit-expected-vulnerable"` marker is written
     but never read by `test.py` (dead config). Harmless; matches chwoot's
     no-branch style, so left in place.
- Status: COMPLETE (after readme fix)
- Next: Ready for Validator — build `test-vulnerable-true-x86_64-linux` and
  confirm `newuser` reaches UID/GID 0; confirm fixed variant does NOT (expected
  fail-by-design). If Batch-2 policy requires standalone VMs for parity with
  Dirty CoW, add a `standaloneVMGenerator` block (optional, non-blocking).

**CVE-2022-0847 (Dirty Pipe):**
- Research summary: uninitialized `pipe_buffer.flags` (`PIPE_BUF_FLAG_CAN_MERGE`)
  lets an unprivileged user splice+write over page-cache bytes of a read-only
  file; kernels 5.8–5.16.10, fixed 5.16.11/5.15.25/5.10.102.
- Oracle type: privilege boundary — overwrite the existing `zoverride` entry in
  `/etc/passwd` at its byte offset to make `vulnuser` UID/GID 0, then
  `ab.check_root_gid(server, "vulnuser")`.
- VM structure: `flake.nix` → `oldKernelTestsGenerator`; vulnerable kernel
  `linuxPackages_5_8` from `oldKernelNixpkgs = b5e903ce…` (locked in
  `flake.lock`), fixed side uses current `pkgs.linuxPackages`. Exploit is the
  canonical Max Kellermann PoC (`exploit.c`) built in-VM. Three consecutive
  `zoverride{,2,3}` users are provisioned to guarantee enough contiguous bytes
  for the payload.
- Gaps found:
  1. (Runtime fragility — Validator must confirm) The PoC cannot write across or
     start on a 4 KiB page boundary. The test computes the live byte offset with
     `grep -b`, and the 3 zoverride entries provide slack, but success depends on
     the runtime `/etc/passwd` layout. This is inherent to Dirty Pipe, not a
     design defect, but it is the one thing that can flake.
  2. (Cosmetic) unused `dirty-pipe-expected-vulnerable` marker, as with PwnKit.
- Status: COMPLETE (pending Validator runtime confirmation of the offset/page
  constraint)
- Next: Ready for Validator — run vulnerable variant; if the write reports
  "cannot write across a page boundary", add another filler user / widen the
  target rather than changing the oracle.

**CVE-2016-5195 (Dirty CoW):**
- Research summary: `mm/gup.c` COW race (`MADV_DONTNEED` vs `/proc/self/mem`
  write) mutates read-only page-cache pages; kernels 2.6.22–4.8.2, fixed 4.8.3
  and stable backports.
- Oracle type: privilege boundary — FireFart `/etc/passwd` overwrite adds
  `firefart` UID/GID 0, then `ab.check_root_gid(server, "firefart")` (120s
  timeout to allow the race to win).
- VM structure: uses `default.nix` + `npins/` (legacy, pre-flakes) — this is OK
  per repo convention. Vulnerable `linuxPackages_4_7` from `nixos-16.03` pin,
  fixed current `pkgs.linuxPackages`; `npins/sources.json` pins both with
  hashes. Also exposes legacy `testVulnerableTrue/False` and standalone
  `vmVulnerableTrue/False` (CLI legacy fallback handles the names). Exploit
  `exploit.c` built with `-pthread -lcrypt`; `libxcrypt` added as buildInput
  only on the modern (non-old-kernel) side, correct since old glibc ships crypt.
- Gaps found: none. `readme.md` matches actual outputs.
- Status: COMPLETE
- Next: Ready for Validator — run `testVulnerableTrue` (old NixOS test driver via
  `oldKernelTestsGenerator`) and confirm `firefart` reaches UID/GID 0. Allow the
  120s race window; may need repeats on a slow host.

---

**Summary:**
- Cases ready for Validator: all three — CVE-2016-5195 (Dirty CoW) and
  CVE-2022-0847 (Dirty Pipe) as-is; CVE-2021-4034 (PwnKit) after the readme
  correction applied in this pass.
- Cases needing remediation: none blocking. Optional/cosmetic follow-ups:
  (a) drop the unused `*-expected-vulnerable` marker files in PwnKit & Dirty
  Pipe (or, if the team prefers explicit passing fixed-side oracles, wire those
  markers into `test.py` using the `gzip-zgrep` branch pattern so
  `test-vulnerable-false` PASSES via a negative assertion instead of
  failing-by-design); (b) optionally add `standaloneVMGenerator` to PwnKit for
  parity with Dirty CoW.
- Blocking Batch 2 commit: NO. All three follow the accepted chwoot privesc
  convention with solid vulnerable-side oracles and correctly pinned
  vulnerable/fixed sources. The only defect found (PwnKit readme) is fixed.

**Files changed by Architect-3:**
- `cves/cve-2021-4034-pwnkit/readme.md` (removed non-existent standalone-VM
  section; documented accurate `pwnkit-exploit` usage).

**Handoff to Validator — explicit asks:**
1. Build/run `test-vulnerable-true-x86_64-linux` for PwnKit & Dirty Pipe, and
   `testVulnerableTrue` for Dirty CoW; capture that `check_root_gid` passes.
2. Confirm the fixed variants behave as expected (fail-by-design under the
   current non-branching convention). Flag to the team if Batch-2 policy instead
   requires fixed variants to PASS — that would turn the two cosmetic marker
   notes above into required remediation.
3. For Dirty Pipe, watch for the page-boundary constraint and report the live
   `grep -b` offset used.

**Safety notes:** All exploits run inside disposable NixOS test VMs, as an
unprivileged `test` user, against in-VM `/etc/passwd`. No host state is touched.
No secrets involved. Nothing outside the repo was read or modified.
