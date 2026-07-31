# NICE Archive CVE Reproduction Workflow Analysis

## Executive Summary

NICE Archive is a **deterministic vulnerability-reproduction framework** designed for historical CVEs. The workflow is **research-first, then implementation**, with explicit boundaries between data gathering and code writing. The framework enforces machine-checkable oracles (not speculative success claims) and requires manual reproduction verification before automated tests.

---

## Recommended Team Structure

For efficient CVE recipe development, assemble a **4-role specialist team**:

| Role | Primary Tasks | Key Responsibilities |
|------|---------------|----------------------|
| **Researcher** 🔍 | CVE discovery + PoC sourcing | Read NVD, upstream advisories, fixing commits; locate existing PoCs; NO code yet |
| **Nix Architect** 🏗️ | Framework design + pinning | Design VM topology; find nixpkgs revisions; write flake.nix + VM modules; choose generator |
| **Test Validator** 🧪 | Manual reproduction + oracle design | Run exploit in VMs manually; translate to test.py; verify assertions against both variants |
| **Reviewer** 🔐 | Quality gate + meta-validation | Verify test oracle captures CVE; check vulnerable/fixed configs; validate readme matches test.py |

**Why this structure:**
- **Sequential phases avoid rework**: Researcher discovers blockers early (no PoC available? stop before Nix time). Architect learns pin strategy from Research phase. Validator ensures oracle correctness.
- **Parallel where possible**: Once Research phase is done, Architect and Validator can work simultaneously (Architect builds flake.nix while Validator explores VMs manually).
- **Handoff gates prevent silent failures**: Each phase ends with a written handoff (facts, pins, manual proof) before next phase starts.
- **Review gate catches meta-errors**: Reviewer validates that the entire case (not just individual parts) correctly reproduces the CVE, preventing false negatives/positives in the test oracle.

**Can a single person hold multiple roles?** Yes, for smaller projects. A **typical small team** could be:
- One person: Researcher + Architect (handles discovery + design)
- One person: Validator (manual reproduction + test.py)
- One person: Reviewer (quality gate)

Or even:
- One person: Researcher (async discoveries for multiple CVEs)
- Rotating pair: Architect + Validator (parallel case development)
- One person: Reviewer (async gate across all cases)

---

## Workflow Phase-by-Phase

### PHASE 1: Research & Discovery (Researcher)

**Goal:** Gather all CVE facts and locate existing PoC *before* writing any code.

**Do NOT proceed to Phase 2 until all of these are documented:**

| Fact | Source Priority | How to Find It |
|------|-----------------|---|
| **CVE ID + description** | NVD, vendor website | nvd.nist.gov or official vendor advisory |
| **Affected software** | Vendor advisory | Which package is vulnerable? (e.g., `sudo`, `openssl`, `jq`) |
| **Vulnerable versions** | NVD + vendor release notes | Exact version range (e.g., `1.9.14` to `<1.9.17p1`) |
| **Fixed version** | NVD + upstream release notes | First version with the fix (e.g., `1.9.17p1`, or a nixpkgs commit) |
| **Fixing commit** | GitHub upstream repo | The actual patch commit hash + URL |
| **Vulnerability class** | Advisor + CVE description | LocalPrivEsc, RCE, DoS, heap overflow, etc. |
| **Exploit precondition** | Advisor + PoC | What must already be true? (e.g., local unprivileged user, network access, auth) |
| **Success condition** | PoC or advisor | What proves the exploit worked? (e.g., attacker gets root shell, file written, crash) |
| **Existing public PoC** | GitHub, exploit-db, vendor, upstream tests | URL + language + whether it works standalone or needs adaptation |
| **Regression test** | Upstream repo (tests/ or t/) | Upstream test that fails on vuln, passes on fixed |
| **Backport risk** | nixpkgs history + advisor | Does an older stable branch already have a backported fix? |

**Research Checklist (in order):**

1. ✅ **NVD baseline**: `nvd.nist.gov/vuln/detail/CVE-XXXX-XXXXX`
   - Record: affected software, versions, severity, link to upstream advisory

2. ✅ **Upstream advisory**: Vendor website or GitHub security advisory
   - Record: exact version ranges, the precise fixing commit, any workarounds

3. ✅ **Fixing commit**: GitHub repo of the affected project
   - Search for the CVE ID in commit messages or tags
   - Record: commit hash, message, files changed, diff URL

4. ✅ **Release notes**: Upstream releases page
   - Confirm the fixed version, any version-specific notes

5. ✅ **Public PoC**: GitHub, SecurityFocus, Exploit Database, upstream test suite
   - Record: URL, language, standalone vs. server/client, any dependencies
   - **Critical**: Try to download and inspect it (without running it yet)

6. ✅ **Regression test**: Upstream test suite (e.g., `tests/`, `t/`, `test_*.py`)
   - Does the upstream project have a test that validates the fix?
   - Record: test file path, how to run it, what it checks

7. ✅ **nixpkgs history check**: Before assuming you need a custom build
   - Use `nix-versions` or GitHub history search to find what nixpkgs commits contain vulnerable + fixed versions
   - Record: commit hashes for both vulnerable and fixed states

8. ✅ **Backport risk assessment**: Read the advisory carefully
   - Look for lines like "also fixed in X.Y.Z" or "backported to stable-5.x"
   - Record: which version branches have backported fixes (these are NOT vulnerable)

**Research Handoff Document (template):**

```markdown
# CVE-XXXX-XXXXX Research Phase Handoff

## CVE Facts
- **CVE ID**: CVE-XXXX-XXXXX
- **Software**: [name]
- **Vulnerable versions**: [range]
- **Fixed versions**: [first fixed version]
- **Class**: [type of vulnerability]
- **Preconditions**: [what must be true for exploit to work]
- **Success indicator**: [what proves it worked]

## Exploit Provenance
- **PoC URL**: [link or "none found"]
- **PoC language**: [Python/C/bash/etc or N/A]
- **PoC status**: [standalone / needs server / needs network / etc]
- **PoC modifications needed**: [describe any changes needed for NixOS VMs]

## Upstream Fix
- **Fixing commit**: [hash]
- **Commit URL**: [GitHub link]
- **Release**: [version that includes the fix]
- **Release date**: [date]

## Regression Test
- **Upstream test file**: [path or "none found"]
- **How to run**: [command]
- **What it validates**: [description]

## Nixpkgs Strategy
- **Vulnerable version in nixpkgs**: [commit hash] or "not available, custom build needed"
- **Fixed version in nixpkgs**: [commit hash or "nixos-unstable"]
- **Backport notes**: [any branches that already have the fix]

## Blockers or Special Cases
- [List any anticipated implementation challenges]

---
**Signed off**: [Researcher name]  
**Date**: [YYYY-MM-DD]
```

**When to STOP (blocker conditions):**
- No public PoC AND no upstream regression test AND no clear exploitation path
- The vulnerability requires a Windows-only environment
- No suitable nixpkgs package/version available (and building from source requires unfamiliar infrastructure)

---

### PHASE 2: Framework Design & Pinning (Nix Architect)

**Goal:** Design the VM topology, select the generator, and pin nixpkgs revisions *before* writing Nix code.

**Inputs from Research phase:**
- Vulnerability class (local PrivEsc, network service, etc.)
- Success condition (file created, crash, output difference, etc.)
- Exploit preconditions (needs unprivileged user? network? specific config?)
- Available PoC or test

**Design Decisions (in order):**

#### 2.1 Choose the VM Topology

**Decision matrix:**

| Scenario | Topology | VMs | Example CVE |
|----------|----------|-----|-------------|
| Local privilege escalation (attacker is unprivileged user on same machine) | Single VM | `server` | sudo PrivEsc, git dubious ownership |
| Local parser crash (e.g., feed malformed input to local program) | Single VM | `server` | jq buffer overflow, Python ctypes overflow |
| Vulnerable server receives crafted network request | Client/Server | `client`, `server` | Heartbleed, OpenSSL early CCS |
| Attacker code isolated from target (safer for research) | Attacker/Server | `attacker`, `server` | libssh auth bypass |
| Multi-service exploitation (mail, proxy, database, etc.) | Multi-service | `attacker`, `server`, `mailserver`, etc. | Apache path traversal with backend |
| Graphical UI required (LibreOffice, browser, X11) | Graphical | `desktop`, `server` | LibreOffice RCE (graphical case) |

**Document the choice:**
- Why this topology?
- Which VMs need to be vulnerable vs. fixed?
- How do VMs communicate?

#### 2.2 Choose the NICE Archive Generator

**Decision table** (from `docs/reporting-vulnerabilities.md`):

| Situation | Generator | Why |
|-----------|-----------|-----|
| Normal package-level vulnerability (most cases) | `testsGenerator` | Default for modern packages |
| Whole system must come from different nixpkgs pins (e.g., vulnerable OpenSSL in system, not pkgs) | `testsGenerator` with `variant = "system"` | Allows per-VM nixpkgs overrides |
| Modern test exists, but humans also need manual VMs for debugging | `testsGenerator` + `standaloneVMGenerator` | Provides both CLI test + manual exploration |
| One or a few VMs must run old kernel / old NixOS while test driver stays modern | `oldKernelTestsGenerator` | Special case for kernel-level vulns |
| Whole reproduction is too old for modern NixOS tests (pre-2015) | `default.nix` + `npins` (manual) | Legacy path for very old cases |

**Decision:** In most cases, start with `testsGenerator`. Only move to more complex generators if testing reveals incompatibility.

#### 2.3 Pin Nixpkgs Revisions

**Priority order for package selection:**

1. ✅ **Existing nixpkgs package at a historical revision** (preferred)
   - Use tools: `nix-versions`, `lazamar.co.uk/nix-versions/`, GitHub history search
   - Example: jq 1.7.1 exists in nixpkgs commit `f45e75f`

2. ✅ **Fetch + import inside the VM module** (e.g., Heartbleed pattern)
   - Use `builtins.fetchTarball` to get source from GitHub
   - Import the tarball's default.nix or build expression inside the module
   - Example: Old OpenSSL source tarball built in the vulnerable VM

3. ✅ **`variant = "system"` with different nixpkgs inputs** (when whole system must differ)
   - Declare `nixpkgs-vulnerable` and `nixpkgs-fixed` as separate flake inputs
   - Pass to generator, which evaluates each VM from the right nixpkgs

4. ⚠️ **`overrideAttrs` for minor version adjustments** (use sparingly)
   - Only if nixpkgs has the package but needs a small source/version tweak
   - Example: package exists but version is 1.2.3, you need 1.2.2

5. ❌ **Build from source** (last resort)
   - Requires non-trivial Nix packaging knowledge
   - Before choosing this, double-check nixpkgs history more thoroughly

**How to find the right nixpkgs commit:**

```bash
# Option 1: Use nix-versions tool
nix shell github:denful/nix-versions -c nix-versions --nixhub --all jq

# Option 2: Search GitHub history directly
# https://github.com/NixOS/nixpkgs/commits/main/pkgs/development/tools/jq/default.nix
# Look for commits that updated the version to the one you need

# Option 3: Use Nix to check what version a commit has
nix eval --raw "github:nixos/nixpkgs/<COMMIT>#jq.version"
```

**Document pin decisions in flake.nix inputs:**

```nix
inputs = {
  nixpkgs-vulnerable.url = "github:NixOS/nixpkgs/<COMMIT-HASH>";
  nixpkgs-fixed.url = "github:NixOS/nixpkgs/nixos-unstable";
  # Comment: vulnerable has jq 1.7.1 (CVE-2024-...), fixed has 1.8.1+
};
```

#### 2.4 Design the Assertion Strategy

**Machine-checkable oracle examples:**

| Success Indicator | Assertion Type | Example |
|-------------------|---|---|
| File created by attacker | `ab.check_file_exists(vm, "/tmp/pwned")` | Exploit writes proof file |
| File contains specific content | `ab.check_file_contains(vm, "/tmp/proof", "secret")` | Leak proof visible in file |
| Attacker gains root | `ab.check_root_gid(vm, "attacker_user")` | After exploit, user is in root group |
| Crash with specific signal | `ab.check_core_dump_exists(vm, expected_signal="SIGSEGV")` | Buffer overflow crashes with SIGSEGV |
| Service log shows attack | `ab.check_file_contains(vm, "/var/log/service.log", "ATTACK_LOGGED")` | Mitigation logged the attack |
| Output differs vulnerable vs. fixed | Custom Python check | Program output before/after fix differs |

**Document:**
- For **vulnerable variant**: what should happen? (exploit succeeds, file created, crash, etc.)
- For **fixed variant**: what should NOT happen? (file doesn't exist, exploit fails, service rejects, etc.)

---

**PHASE 2 Handoff Document (template):**

```markdown
# CVE-XXXX-XXXXX Framework Design Handoff

## VM Topology
- **Design**: [description of VM layout]
- **VMs**: [names and roles]
- **Communication**: [how do VMs talk?]
- **Why this topology**: [justification]

## Generator Choice
- **Generator**: [testsGenerator / testsGenerator + variant / oldKernelTestsGenerator / etc.]
- **Justification**: [why this generator fits]

## Nixpkgs Pinning Strategy
- **Vulnerable package**: [nixpkgs commit] or [manual fetch pattern]
- **Fixed package**: [nixpkgs commit or nixos-unstable]
- **VM topology for variant**: [package / system / old-kernel]

### Vulnerable Pins
- **Software + version**: [package-name version]
- **nixpkgs commit**: [HASH]
- **How verified**: [nix-versions / GitHub history / etc]

### Fixed Pins
- **Software + version**: [package-name version]
- **nixpkgs commit**: [HASH]
- **How verified**: [nix-versions / GitHub history / etc]

## Assertion Strategy

### Vulnerable Variant
- **Success condition**: [what proves exploit worked]
- **Assertion**: [ab.check_* helper or custom Python]

### Fixed Variant
- **Non-existence**: [what should NOT happen]
- **Assertion**: [ab.check_* helper or custom Python]

## flake.nix Template
```nix
{
  inputs = {
    nixpkgs-vulnerable.url = "github:NixOS/nixpkgs/...";
    nixpkgs-fixed.url = "github:NixOS/nixpkgs/...";
    nice-archive-lib.url = "../../src";
  };
  
  outputs = { nixpkgs-vulnerable, nixpkgs-fixed, nice-archive-lib, ... }:
    nice-archive-lib.testsGenerator {
      title = "cve-xxxx-nnnn-name";
      nixpkgs = nixpkgs-fixed;
      caseDir = ./.;
      testScriptPath = ./test.py;
      
      VMs.server = {
        configPath = ./vm-server.nix;
        variant = "package"; # or "system"
      };
    };
}
```
(fill in actual values)

---
**Signed off**: [Architect name]  
**Date**: [YYYY-MM-DD]
```

---

### PHASE 3: Implementation (Nix Architect + Test Validator, parallel)

**This phase has two parallel streams:**

#### Stream A: Write Nix files (Architect)

**Files to create:**
1. `cves/cve-xxxx-nnnn-name/flake.nix` — generator + inputs
2. `cves/cve-xxxx-nnnn-name/vm-server.nix` — NixOS module (and vm-attacker.nix, etc. if needed)
3. `cves/cve-xxxx-nnnn-name/test.py` — automated test (stub with manual reproduction commands first)
4. `cves/cve-xxxx-nnnn-name/readme.md` — documentation

**Architect workflow:**

1. Copy Nix template files from an existing case (e.g., chwoot)
2. Edit `flake.nix` with correct inputs and generator config
3. Write `vm-*.nix` modules:
   - Check `isVulnerable` flag and branch on package selection
   - Add exploit files (if any) using `pkgs.runCommand`
   - Set up services, network firewall, users as needed
4. Create stub `test.py` with just `start_all()` and manual commands in comments
5. Commit to git (NICE Archive CLI requires files in git before flake evaluation)

#### Stream B: Manual Reproduction (Validator)

**Validator workflow (runs in parallel with Architect's Nix writing):**

1. Start the interactive scenario:
   ```bash
   nice-archive scenario \
     --case cve-xxxx-nnnn-name \
     --vulnerable true \
     --popup false
   ```

2. In another terminal, SSH into the VM using the printed command:
   ```bash
   ssh -o User=root vsock-mux://...../server_host.socket
   ```

3. Inside the VM, manually reproduce the exploit:
   - Run the exploit step-by-step (if it's a script)
   - Trigger the vulnerability manually (if it's a command sequence)
   - Inspect the result

4. Document the exact commands and the output

5. Run on the fixed variant (same flow, but with `--vulnerable false`)

6. Confirm the exploit fails or the effect is absent on the fixed variant

**Key debugging paths (from docs):**

| Debugging Need | Path |
|---|---|
| Modern library-backed case | `nice-archive scenario --vulnerable true --popup false`, then SSH |
| Manual VM setup needed | Use `standaloneVMGenerator` and run `nice-archive vm --name server-vulnerable` |
| Old kernel special case | Use old-kernel generator; check kernel version with `uname -r` inside VM |

---

### PHASE 4: Translate Manual Proof to Automated Test (Validator)

**Validator: Write test.py**

After manual reproduction succeeds:

1. **Translate manual commands to Python test-driver API:**

   ```python
   # Manual: ssh into VM, run "exploit", check file
   # Becomes:
   server.wait_for_unit("multi-user.target")
   server.succeed("exploit")  # if exploit must exit 0
   status, output = server.execute("exploit")  # if you need to inspect the output
   ```

2. **Use assertion blocks to check the security property:**

   ```python
   if variant == "vulnerable":
       # On vulnerable version, exploit should succeed
       ab.check_file_exists(server, "/tmp/pwned")
       ab.check_file_contains(server, "/tmp/proof", "hacked")
   else:
       # On fixed version, exploit should NOT create the file
       ab.check_file_exists(server, "/tmp/pwned", is_existing=False)
   ```

3. **Use `variant` variable to branch** (set by NICE Archive framework):

   ```python
   if variant == "vulnerable":
       # assertions for vulnerable behavior
   elif variant == "fixed":
       # assertions for fixed behavior
   else:
       assert False, f"Unknown variant: {variant}"
   ```

4. **Run both test variants:**

   ```bash
   nice-archive test --case cve-xxxx-nnnn-name --vulnerable true --log live
   nice-archive test --case cve-xxxx-nnnn-name --vulnerable false --log live
   ```

5. **Adjust test.py until both pass.**

---

### PHASE 5: Documentation & Final Verification (Architect + Validator)

**Jointly document:**

1. **readme.md**: Explain the CVE, topology, exploit, and how to run it
   - Include manual reproduction commands (from Validator's work in Phase 3)
   - Point to `test.py` as the machine-checkable oracle
   - List exploit provenance

2. **Final verification checklist** (from docs):

   ```
   - [ ] Vulnerable test demonstrates the exploit
   - [ ] Fixed test demonstrates mitigation or absence of effect
   - [ ] Assertion checks the security property, not just command completion
   - [ ] test.py ends with framework assertion blocks
   - [ ] Exploit provenance is documented in readme.md
   - [ ] flake.nix uses the appropriate generator
   - [ ] VM names are clear and match test.py
   - [ ] Manual reproduction steps in readme.md use scenario SSH or popup VMs
   - [ ] readme.md points to test.py as the automated oracle
   - [ ] Generated artifacts (logs, result symlinks, .qcow2, .nixos-test-history) are not committed
   ```

---

### PHASE 6: Reviewer Gate (Reviewer)

**Goal:** Validate that the entire case correctly reproduces the CVE as described, catching meta-level errors that individuals may miss.

**Reviewer Checklist (meta-validation):**

**Oracle Correctness** ✓
- Does the test oracle (assertions in test.py) actually measure what the CVE describes?
  - Example: CVE describes privilege escalation → oracle checks `ab.check_root_gid(vm, unprivileged_user)`, not just "exploit command ran"
  - Example: CVE describes information leak → oracle checks `ab.check_file_contains(vm, "/leak.txt", "secret_data")`, not just file exists
- Are assertions present for BOTH vulnerable and fixed variants?
- Do assertions use `assertion_blocks` helpers, not vague `assert` statements?

**Configuration Correctness** ✓
- **Vulnerable variant**: Does it truly produce the vulnerable behavior?
  - Run `nice-archive test --case cve-xxx --vulnerable true` and verify it passes (test proves vulnerability)
  - Check that vulnerable VM actually has the old version (not accidentally fixed)
- **Fixed variant**: Does it truly mitigate the vulnerability?
  - Run `nice-archive test --case cve-xxx --vulnerable false` and verify it passes (test proves mitigation)
  - Check that fixed VM actually has the new version (not accidentally vulnerable)
- Are both tests independent? (Can you run either one in isolation?)

**Documentation Alignment** ✓
- Does readme.md description match the test.py assertions?
  - Example: If readme says "exploit writes file", does test.py check `ab.check_file_exists`?
- Are manual reproduction steps in readme.md accurate and verified?
- Is exploit provenance documented (URL, license, modifications)?
- Does readme.md point readers to test.py as the oracle?

**Research Provenance** ✓
- Are CVE facts in readme.md traceable to the Research Handoff?
- Do vulnerable/fixed versions match nixpkgs pins in flake.nix?
- Is the PoC source URL in readme.md the same as the one in Research Handoff?
- Any discrepancies between what was discovered and what was implemented?

**Arch & Implementation Quality** ✓
- Is the generator choice justified (testsGenerator vs. oldKernelTestsGenerator vs. standalone)?
- Are VM names clear and match test.py variable names?
- Is graphical/OCR/special case handling correct if applicable?
- Are there any obvious Nix errors (syntax, missing inputs, circular deps)?

**Reviewer Actions:**

| Finding | Action |
|---------|--------|
| All checks pass | **APPROVE** — case is merge-ready; add to CI/test suite |
| Minor fixes needed (typos, comments) | Request small changes; can be minor or auto-fixed |
| Assertion doesn't measure CVE correctly | **REQUEST REVISION** — Validator must update test.py + re-run tests |
| Vulnerable/fixed config is wrong (false positive/negative) | **REJECT** — Architect must fix VM config; Validator must re-test |
| Documentation severely mismatches implementation | **REJECT** — Architect + Validator must reconcile; document why |
| No exploit provenance or PoC source missing | **REJECT** — Validator must add attestation; Researcher must clarify sourcing |

**Reviewer Handoff Template:**

```markdown
# CVE-XXXX-XXXXX Reviewer Gate Report

**Case**: `cves/cve-xxxx-nnnn-short-name/`  
**Status**: [APPROVED / APPROVED WITH MINOR FIXES / NEEDS REVISION / REJECTED]

## Oracle Validation
- ✅/❌ Assertions measure the CVE, not just command completion
- ✅/❌ Both vulnerable and fixed variants have assertions
- ✅/❌ Using assertion_blocks helpers (not vague assert)

## Configuration Validation
- ✅/❌ Vulnerable test passes and proves vulnerability
- ✅/❌ Fixed test passes and proves mitigation
- ✅/❌ Both variants can run independently

## Documentation Alignment
- ✅/❌ readme.md matches test.py assertions
- ✅/❌ Manual reproduction steps are accurate
- ✅/❌ Exploit provenance documented
- ✅/❌ readme.md points to test.py as oracle

## Research Provenance
- ✅/❌ CVE facts in readme match Research Handoff
- ✅/❌ Version numbers match flake.nix pins
- ✅/❌ PoC source URL is consistent

## Architecture Quality
- ✅/❌ Generator choice is justified
- ✅/❌ VM names are clear and match test.py
- ✅/❌ No obvious Nix errors

## Comments
[List any issues found, or write "none"]

## Requested Changes
[If REVISION needed, list specific actions for Validator/Architect]

---
**Reviewed by**: [Reviewer name]  
**Date**: [YYYY-MM-DD]  
**Approval**: [Name signature or GitHub approval]
```

3. **Handoff summary:**

   ```
   Implemented:
   - Files: flake.nix, vm-server.nix, test.py, readme.md
   - Generator: testsGenerator
   - VM topology: single server
   - Vulnerable version: jq 1.7.1 (nixpkgs f45e75f)
   - Fixed version: jq 1.8.1 (nixpkgs-25.11)
   
   Verified:
   - Command: nice-archive test --case cve-xxxx-nnnn-name --vulnerable true
   - Result: test passed, assertion_blocks verified file written
   - Log file: debug-vulnerable.log
   
   Known limitations: none
   ```

---

## Multi-CVE Parallel Execution

NICE Archive is designed to support **multiple independent CVE cases being developed simultaneously** with minimal coordination overhead.

### Why Parallel Development Works

Each CVE case is **completely isolated**:
- Own directory: `cves/cve-xxxx-nnnn-name/` (separate from others)
- Own flake.nix with independent inputs (no shared pinning)
- Own test.py with independent test driver setup
- Own VM modules with isolated configurations
- CLI runs each case independently: `nice-archive test --case cve-1 ...` and `nice-archive test --case cve-2 ...` can run in parallel

**Git isolation**: Each case lives in its own directory tree. Two teams can edit `cves/cve-1111-xxxx/` and `cves/cve-2222-yyyy/` simultaneously with zero merge conflicts (unless both edit the same case).

### Coordination Patterns for Multi-CVE Teams

#### Pattern 1: Rotating Researcher + Pair Architect/Validator (Lightweight)

**Setup**: 
- 1 Researcher (discovers multiple CVEs, async)
- 2-person Architect/Validator pair (implements cases sequentially)
- 1 Reviewer (async gate)

**Workflow**:
```
Week 1:
  Researcher: Discovers CVE-1, CVE-2, CVE-3 (PHASE 1 for each)
  Architect/Validator: Working on CVE-0 (PHASES 3-5)
  Reviewer: Reviews completed CVE (PHASE 6 for previous case)

Week 2:
  Researcher: Discovers CVE-4, CVE-5 (deep dive on blockers)
  Architect/Validator: Switch to CVE-1 (PHASES 3-5, using Researcher's handoff)
  Reviewer: Reviews CVE-1 (PHASE 6)

Week 3:
  Similar pattern, now doing CVE-2
```

**Pros**: Minimal team size, clear sequential responsibility  
**Cons**: Only one case in active development at a time; Architect/Validator becomes bottleneck

#### Pattern 2: Parallel Teams (One per CVE)

**Setup**: 
- Each CVE gets a dedicated 4-person team (Researcher, Architect, Validator, Reviewer)
- Teams work independently on separate CVEs
- Central merge gate (CI + optional human review)

**Workflow**:
```
Team A: CVE-1 (all phases in parallel)
Team B: CVE-2 (all phases in parallel)
Team C: CVE-3 (all phases in parallel)

When complete, each team's case goes through central merge gate
  Git merge: case is added to main branch
  CI runs: nice-archive test --case cve-xxxx --vulnerable true/false
  Release: new case is available via nice-archive list-cves
```

**Pros**: Maximum parallelism; full team context per CVE; fast throughput  
**Cons**: Requires more people; may have redundant research/review work

#### Pattern 3: Cascading Teams (Hybrid)

**Setup**:
- 1 Researcher (discovers, PHASE 1 for N CVEs)
- 2-3 Architect/Validator pairs (each pair takes 1-2 cases from Researcher's queue)
- 1-2 Reviewers (async gate)

**Workflow**:
```
Researcher: CVE-1, CVE-2, CVE-3 discoveries (async, produces Phase 1 handoffs)

Pair A: CVE-1 PHASES 2-5 (while Researcher does CVE-2)
Pair B: CVE-2 PHASES 2-5 (once Researcher finishes)
Pair C: CVE-3 PHASES 2-5 (once Researcher finishes)

Reviewer A: Reviews CVE-1 (while Pair A finishes)
Reviewer B: Reviews CVE-2 (parallel)

Result: 3 CVEs in parallel, but only 2 Researcher waiting for next batch
```

**Pros**: Good balance of parallelism and team efficiency  
**Cons**: Coordination overhead for queue management

### Coordination Tools & Practices

#### Shared Coordination File (Optional)

Create `.squad/cve-assignment.md` to track concurrent work:

```markdown
# CVE Assignment Tracker

## In Progress

| CVE | Team | Phase | ETA | Notes |
|-----|------|-------|-----|-------|
| CVE-1111-xxxx | Team A | PHASE 4 (test.py automation) | 2026-08-05 | Waiting on PoC |
| CVE-2222-yyyy | Team B | PHASE 2 (design) | 2026-08-08 | Arch choosing generator |
| CVE-3333-zzzz | Team C | PHASE 1 (research) | 2026-08-12 | Discovering PoC |

## Blocked

| CVE | Blocker | Team | Action Required |
|-----|---------|------|-----------------|
| CVE-4444-aaaa | No public PoC | Team A | Escalate? Or skip? |

## Completed (Awaiting Review)

| CVE | Team | Reviewer | Status |
|-----|------|----------|--------|
| CVE-5555-bbbb | Team D | Reviewer A | Approved |
| CVE-6666-cccc | Team E | Reviewer B | Needs revision |

## Merged

| CVE | Date | Notes |
|-----|------|-------|
| CVE-0000-example | 2026-08-01 | First case merged |
```

#### Git Workflow for Multiple Teams

**Branch strategy** (simple):
1. Each team works on their own branch: `feature/cve-1111-xxxx`, `feature/cve-2222-yyyy`
2. No cross-team merges until both cases pass review
3. When approved, merge to `main` one case at a time (or batched if no conflicts)
4. Pull `main` between merges to stay in sync

**Example**:
```bash
# Team A
git checkout -b feature/cve-1111-xxxx
# ... do PHASES 1-5, commit frequently
git push origin feature/cve-1111-xxxx
# Wait for review, then:
git pull origin main
git checkout main
git merge feature/cve-1111-xxxx
git push origin main

# Team B (parallel, on different case)
git checkout -b feature/cve-2222-yyyy
# ... same flow, no conflicts with Team A
```

#### CI Integration (Recommended)

Add a CI job that runs all cases automatically:

```yaml
# .github/workflows/test-cves.yml
on: [push, pull_request]

jobs:
  test-cases:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: cachix/install-nix-action@v18
      - run: |
          for case in $(nice-archive list-cves | awk '{print $1}'); do
            echo "Testing $case..."
            nice-archive test --case "$case" --vulnerable true --log file logs/$case-vuln.log
            nice-archive test --case "$case" --vulnerable false --log file logs/$case-fixed.log
          done
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-logs
          path: logs/
```

This ensures every PR (new cases or fixes to existing ones) passes tests before merge.

#### Async Reviewer Pattern

Since review can be a bottleneck, use async handoffs:

1. **Validator**: When test.py passes both variants, creates PR with `[READY FOR REVIEW]` label
2. **Reviewer**: Picks up PRs with that label, reviews asynchronously (no meeting needed)
3. **Reviewer**: Comments with verdict (APPROVE / REQUEST REVISION / REJECT)
4. **Original team**: Addresses feedback if needed, requests re-review
5. **Reviewer**: Final approval → merge

**GitHub template** (PR description):

```markdown
## CVE Reproduction Case: CVE-XXXX-NNNN

**Case directory**: `cves/cve-xxxx-nnnn-short-name/`

**Phases completed**:
- ✅ Phase 1 (Research)
- ✅ Phase 2 (Design)
- ✅ Phase 3 (Implementation)
- ✅ Phase 4 (Automated tests)
- ✅ Phase 5 (Documentation)

**Test results**:
- Vulnerable: `nice-archive test --case cve-xxxx-nnnn-short-name --vulnerable true` → PASSED
- Fixed: `nice-archive test --case cve-xxxx-nnnn-short-name --vulnerable false` → PASSED

**Ready for reviewer**: [Reviewer name/assignment]

[Link to Phase 5 handoff or checklist]
```

### Handling Merge Conflicts

**Rare scenario** (same case edited by multiple teams):
- Only happens if two teams independently decide to work on the same CVE
- **Prevention**: Check `.squad/cve-assignment.md` or issue tracker before starting
- **Resolution**: First team to merge wins; second team must rebase on main and re-test

**Likely scenario** (different cases, no conflicts):
- Git merges linearly, no conflicts at all
- Each case is independent → no shared state to conflict

### Scaling Guidelines

| Team Size | Recommended Structure | Max Concurrent Cases |
|-----------|----------------------|----------------------|
| 1-2 people | Researcher + Validator (shared roles) | 1-2 |
| 3-4 people | Researcher + (Architect/Validator pair) + Reviewer | 2-3 |
| 5-8 people | Pattern 2 (Parallel Teams) or Pattern 3 (Cascading) | 4-6 |
| 8+ people | Multiple independent squads, each following Pattern 2 | 6+ |

---

## Tool Usage Reference

### CLI Workflow (from repository root)

```bash
# List all CVE cases
nice-archive list-cves

# List VMs for a specific case
nice-archive list-vms --case cve-xxxx-nnnn-name

# Run vulnerable test with live output
nice-archive test \
  --case cve-xxxx-nnnn-name \
  --vulnerable true \
  --log live

# Run fixed test with saved log
nice-archive test \
  --case cve-xxxx-nnnn-name \
  --vulnerable false \
  --log file debug-fixed.log

# Start interactive scenario (SSH backdoor mode)
nice-archive scenario \
  --case cve-xxxx-nnnn-name \
  --vulnerable true \
  --popup false

# Run a standalone VM (for cases with standaloneVMGenerator)
nice-archive vm \
  --case cve-xxxx-nnnn-name \
  --name server-vulnerable
```

### Interactive Debugging: SSH Backdoor Pattern (Recommended)

**Why SSH is better than the REPL prompt:**
- REPL has a terminal control-sequence bug that corrupts input after the first line
- SSH runs commands directly inside the VM, bypassing the REPL entirely

**Steps:**

1. Start scenario in terminal 1:
   ```bash
   nice-archive scenario --case cve-xxxx-nnnn-name --vulnerable true --popup false
   ```

2. CLI prints SSH commands. Copy one, e.g.:
   ```
   server: ssh -o User=root vsock-mux://run/user/1000/tmp.abc/server_host.socket
   ```

3. In terminal 2, paste and run:
   ```bash
   ssh -o User=root -o StrictHostKeyChecking=no "vsock-mux://run/user/1000/tmp.abc/server_host.socket" 'your-command-here'
   ```

4. Run exploit commands non-interactively. No REPL corruption.

5. To exit scenario, press Ctrl+D in terminal 1 and choose "Yes" to kill VMs.

**Fallback: If SSH doesn't work**
- Use the REPL, but only send first line: `start_all(); server.wait_for_unit("multi-user.target")`
- Then immediately switch to SSH if available
- If SSH unavailable, use standalone VMs instead (Path B in docs)

---

## Critical Rules & Pitfalls

### Anti-Patterns (AVOID THESE)

❌ **Do NOT build vulnerable software from source** before checking nixpkgs history  
✅ Use `nix-versions` or GitHub history to find the commit containing the vulnerable version

❌ **Do NOT skip manual reproduction in a VM**  
✅ Always run the exploit manually first, in an interactive scenario or standalone VM

❌ **Do NOT use only `assert` statements in test.py**  
✅ End tests with `assertion_blocks` helpers (e.g., `ab.check_file_exists`, `ab.check_file_contains`)

❌ **Do NOT check only that an exploit command exited**  
✅ Check the security effect (e.g., "file was created" or "privilege escalation succeeded")

❌ **Do NOT omit exploit provenance**  
✅ Document the PoC source URL, whether you modified it, and why

❌ **Do NOT rely on REPL interactive input for critical tests**  
✅ Use SSH backdoor or put all critical commands in test.py (automated driver)

❌ **Do NOT commit generated artifacts**  
✅ `.gitignore` should exclude: generated logs, `result` symlinks, `.qcow2` files, `.nixos-test-history`

### Gotchas from Repository Memory

**Crash-based oracles (glibc fortify, malloc errors):**
- Message goes to `/dev/tty`, not fd 2, corrupting the test-driver protocol
- **Fix**: Run crashing process under `setsid -w PROG > /tmp/out 2>&1 </dev/null`, then read the file

**PoC crash reliability on host:**
- Verify the PoC actually crashes on the HOST before spending VM build time
- Hardened nixpkgs builds sometimes don't crash on single-byte heap overflows
- **Action**: Build the pinned package, run PoC directly, confirm crash

**Backported fixes invalidate old-version pins:**
- An "old" version in a stable branch might already have a backported fix
- **Example**: Git 2.33.3 (nixos-21.11) already has CVE-2022-24765 fix, so it's not a valid vulnerable pin
- **Action**: Read the advisory for "also fixed in X.Y.Z" and avoid those branches

---

## Handoff Template (for Phase 4 Completion)

When a case is ready for merge:

```
## CVE-XXXX-XXXXX Implementation Complete

**Case directory**: `cves/cve-xxxx-nnnn-short-name/`

**Files added/changed**:
- flake.nix (generator config + inputs)
- vm-server.nix (NixOS module)
- test.py (automated test with assertions)
- readme.md (human-readable documentation)
- exploit/ (optional: PoC files or scripts)

**Generator used**: testsGenerator (or variant)

**VM topology**: Single server (or describe actual topology)

**Vulnerable version**: [software-name version]  
Nixpkgs commit: [HASH]  
How verified: [nix-versions / GitHub / etc]

**Fixed version**: [software-name version]  
Nixpkgs commit: [HASH]  
How verified: [nix-versions / GitHub / etc]

**PoC or trigger**:
- Source: [URL]
- Language: [Python/C/bash]
- Modifications: [describe changes for NixOS VMs]

**Oracle**:
- Vulnerable: [ab.check_* helper(s) used]
- Fixed: [ab.check_* helper(s) used]

**Commands run**:
```bash
nice-archive test --case cve-xxxx-nnnn-name --vulnerable true --log live
nice-archive test --case cve-xxxx-nnnn-name --vulnerable false --log live
```

**Results observed**:
- Vulnerable test: PASSED (output summary)
- Fixed test: PASSED (output summary)

**Known limitations**:
- [List, or write "none"]

**Safety notes**:
- [Any special handling, or "standard precautions"]

**References**:
- [NVD link]
- [Vendor advisory]
- [Fixing commit URL]
- [PoC source URL]
```

---

## Summary: Team & Workflow at a Glance

### Single-CVE Case (Per-Team Workflow)

```
PHASE 1: Research (Researcher)
├─ Read NVD, advisories, fixing commits
├─ Locate public PoC (don't craft one)
├─ Find nixpkgs revisions for vulnerable + fixed
├─ Document in handoff (facts + pins)
└─ STOP if blockers found

PHASE 2: Design (Architect)
├─ Choose VM topology (single/client-server/graphical/etc)
├─ Choose generator (testsGenerator default, else oldKernel/standalone)
├─ Pin exact nixpkgs revisions
├─ Design assertion strategy (what proves vulnerable? fixed?)
└─ Document in handoff (flake template + design)

PHASE 3: Parallel Streams
├─ Architect: Write flake.nix, vm-*.nix, stub test.py
├─ Validator: Start scenario, SSH into VMs, manually reproduce exploit
└─ CONVERGE on shared manual reproduction proof

PHASE 4: Automate (Validator)
├─ Translate manual commands to test.py
├─ Use assertion_blocks for oracle
├─ Test vulnerable + fixed variants
└─ Iterate until both pass

PHASE 5: Documentation (Architect + Validator)
├─ Write readme.md
├─ Final verification checklist
├─ Create handoff summary
└─ READY FOR REVIEW

PHASE 6: Reviewer Gate (Reviewer) ⭐
├─ Validate oracle captures CVE correctly
├─ Check vulnerable/fixed configs are actually vulnerable/fixed
├─ Verify readme matches test.py
├─ Verify research provenance
└─ APPROVE → merge-ready, or REQUEST REVISION
```

### Multi-CVE Organization (Cross-Team Coordination)

```
Pattern 1 (Lightweight, 1-2 teams):
  Researcher: CVE-1, CVE-2, CVE-3 discoveries (async queue)
    ↓ PHASE 1 handoff
  Architect/Validator pair: Sequential CVE-1 → CVE-2 → CVE-3
    ↓ PHASES 2-5 per case
  Reviewer: Async gate, reviews as cases complete

Pattern 2 (Parallel, 3+ teams):
  Team A: CVE-1 (all phases in parallel)
  Team B: CVE-2 (all phases in parallel)  
  Team C: CVE-3 (all phases in parallel)
    ↓ Each team completes PHASE 6
  Central merge gate: CI validates both variants pass
    ↓ Each case merged independently to main

Pattern 3 (Cascading, 4-8 people):
  Researcher: Discovers N CVEs (PHASE 1 queue)
    ↓ Handoffs to:
  Architect/Validator pairs (2-3): Parallel PHASES 2-5
    ↓
  Reviewer(s): Async PHASE 6 validation
```

**Key insight**: Each CVE case is **completely isolated** (`cves/cve-xxxx/` directory), so:
- No merge conflicts between different CVEs
- Teams can work in parallel without coordination
- CI runs each case independently
- Reviewer can gate individual cases without blocking others
- Easy to scale from 1 team to N teams

See "Multi-CVE Parallel Execution" section for detailed coordination patterns, git workflows, CI integration, and scaling guidelines.

---

## References & Further Reading

- **Framework docs**: `docs/README.md`, `docs/reporting-vulnerabilities.md`, `docs/nice-archive-libs.md`
- **Existing cases**: `cves/cve-2025-32463-chwoot/`, `cves/cve-2014-0160-heartbleed/`, `cves/cve-2022-0847-dirty-pipe/`
- **Nixpkgs tools**: [nix-versions](https://github.com/denful/nix-versions), [lazamar nix-versions web](https://lazamar.co.uk/nix-versions/)
- **Framework capabilities**: `nice-archive.py`, runner module exports
- **Repository memory**: `/memories/repo/nice-archive-notes.md` (jq pins, crash handling, backport warnings)
