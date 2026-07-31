# Work Routing

How to decide who handles what.

## Routing Table

| Work Type | Route To | Examples |
|-----------|----------|----------|
| CVE research & discovery | Researcher | Gather CVE facts, find PoCs, check nixpkgs history, assess backports |
| CVE framework design | Architect | VM topology, generator selection, nixpkgs pinning, flake.nix design |
| CVE manual reproduction | Validator | Run exploits in VMs via SSH, verify vulnerable/fixed configs, capture proof |
| CVE test automation | Validator | Translate manual commands to test.py, write ab.check_* assertions |
| CVE quality gate | Reviewer | Validate oracle correctness, config soundness, documentation alignment |
| Code review | Reviewer | Review PRs, check Nix code quality, suggest improvements |
| Testing | Validator | Write tests, find edge cases, verify fixes |
| Scope & priorities | Researcher | What CVEs to investigate next, CVE prioritization |
| Session logging | Scribe | Automatic — never needs routing |
| RAI review | Rai | Content safety, bias checks, credential detection, ethical review |

## Issue Routing

| Label | Action | Who | Notes |
|-------|--------|-----|-------|
| `cve-research` | Triage: assign to Researcher for Phase 1 | Researcher | CVE discovery, PoC sourcing, nixpkgs history |
| `cve-architecture` | Assign to Architect after Research Handoff | Architect | Design flake.nix and VM topology |
| `cve-testing` | Assign to Validator after Architect hands off | Validator | Manual reproduction + test.py automation |
| `cve-review` | Assign to Reviewer after Validator completes | Reviewer | Phase 6 quality gate before merge |
| `squad` | Triage: analyze issue, assign appropriate `squad:{member}` label | Coordinator | Meta-routing — use role-specific labels above |
| `squad:{name}` | Pick up issue and complete the work | Named member | Standard GitHub workflow |

### CVE Case Workflow

1. **New CVE arrives** → Label with `cve-research`
2. **Researcher completes Phase 1** → Create Research Handoff issue/artifact
3. **Coordinator** assigns `cve-architecture` label → Architect starts Phase 2
4. **Architect completes Phase 2-3** → Push Nix code to branch
5. **Coordinator** assigns `cve-testing` label → Validator starts Phase 3-4
6. **Validator completes Phase 4** → Create PR with test.py passing both variants
7. **Coordinator** assigns `cve-review` label → Reviewer starts Phase 6
8. **Reviewer approves** → Merge to main
9. **Case is live** → `nice-archive list-cves` shows it immediately

### How Issue Assignment Works

1. When a GitHub issue gets the `cve-research` label, **Researcher** picks it up in the next session.
2. When Phase 1 is complete, **Coordinator** (or human) moves to `cve-architecture` label → **Architect** picks up.
3. When Architect hands off Nix code, **Coordinator** moves to `cve-testing` label → **Validator** picks up.
4. When Validator completes test.py, **Coordinator** moves to `cve-review` label → **Reviewer** picks up.
5. When Reviewer approves, case is ready for merge.
6. Members can escalate by removing their label and adding a comment explaining blocker.

## Rules

1. **Eager by default** — spawn all agents who could usefully start work, including anticipatory downstream work.
2. **Scribe always runs** after substantial work, always as `mode: "background"`. Never blocks.
3. **Quick facts → coordinator answers directly.** Don't spawn an agent for "what port does the server run on?"
4. **When two agents could handle it**, pick the one whose domain is the primary concern.
5. **"Team, ..." → fan-out.** Spawn all relevant agents in parallel as `mode: "background"`.
6. **Anticipate downstream work.** If a feature is being built, spawn the tester to write test cases from requirements simultaneously.
7. **Issue-labeled work** — when a `squad:{member}` label is applied to an issue, route to that member. The Lead handles all `squad` (base label) triage.

## CVE-Specific Workflow Rules

1. **Phase gates are hard stops** — each phase must complete before the next begins:
   - Research (Phase 1) → Design (Phase 2) → Implementation (Phase 3) → Automation (Phase 4) → Documentation (Phase 5) → Review (Phase 6)
   - Use issue labels (`cve-research`, `cve-architecture`, `cve-testing`, `cve-review`) to enforce phase progression.

2. **Researcher works async** — discovers N CVEs in parallel; produces Research Handoff documents.

3. **Architect + Validator run in parallel** — once Research Handoff exists:
   - Architect designs flake.nix (Phase 2) + writes Nix code (Phase 3)
   - Validator manually reproduces exploit in interactive scenarios while Architect works (Phase 3)
   - Both converge on shared manual proof before Validator writes test.py (Phase 4)

4. **Reviewer gates before merge** — Reviewer runs both test variants, validates oracle, checks configs, reviews docs before APPROVE/REJECT.

5. **Parallel multi-CVE support** — different CVE cases can be in different phases simultaneously:
   - CVE-1 in Phase 1 (Researcher discovering)
   - CVE-2 in Phase 3 (Architect + Validator working)
   - CVE-3 in Phase 6 (Reviewer validating)
   - No conflicts because each case has its own directory and git branch.

6. **No speculation** — if Researcher finds no public PoC and no upstream test, STOP. Don't proceed to Architect/Validator.

7. **Manual before automated** — Validator must prove exploit works manually (via SSH) before writing test.py.
