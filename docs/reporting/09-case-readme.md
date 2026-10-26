# 9. Write the case README

Write a compact, self-contained account of this CVE and its observed result.
Support version and fix claims with authoritative sources and validation
claims with actual command output. Do not cite another case as authority for
this case. Label every command or variant that was not run.

Use this Markdown structure and replace the placeholders with case-specific
facts. Include the marked LLM subsection only when an LLM agent performed the
reproduction.

````markdown
# CVE-YYYY-NNNN: short title

## Summary

- **Affected software:** <product and component>
- **Impact:** <security effect>
- **Affected range:** <authoritative version range>
- **Selected versions:** <vulnerable version> and <fixed version>
- **Disclosure date:** <YYYY-MM-DD, if relevant and verified>

## What goes wrong

Explain the flaw, the security boundary it crosses, and what the fix changes.

## How the reproduction works

State the generator, VM roles, package or system pins, exact software source
(nixpkgs revision, upstream archive or repository, or registry), versions,
artifact URLs, and verified hashes. Name the trigger, target-unique marker,
evidence location, and vulnerable/fixed oracle.

Briefly explain why the selected packaging method fits the required versions
and environment. For a source-build fallback, name the concrete limitation of
historical package or system pins; keep exact source details in `Sources and
local adaptations` without repeating them.

For more than one VM, show the numbered trigger and evidence flow:

```text
[Attacker VM] --[1] trigger--> [Target VM]
[Attacker VM] <--[2] evidence-- [Target VM]
```

Explain [1] and [2] in prose and say where fixed behavior diverges. Replace
this diagram with the actual roles and communication path.

## Justification

Explain unusual packaging, topology, trigger adaptation, direct assertions,
or validation choices. If none apply, say the standard workflow was followed.

## Running the reproduction

### Manual

Give the verified scenario or standalone VM command. Show each guest command
in order, with its expected effect and the evidence actually observed in each
variant. Mark any unexecuted path **not run**.

### Automated

```bash
nice-archive test --case cve-yyyy-nnnn-short-name --vulnerable true
nice-archive test --case cve-yyyy-nnnn-short-name --vulnerable false
```

State the expected and observed result for each command. Explain how the
assertions prove the security effect and its absence in the fixed variant.

## Results

| Variant | Expected | Observed | Status |
| --- | --- | --- | --- |
| Vulnerable | Security effect | Actual target-side evidence or not run | pass/fail/not run |
| Fixed | Effect absent; target healthy | Actual evidence or not run | pass/fail/not run |

## Sources and local adaptations

- Advisory and affected range: <authoritative URL>
- Fix and release: <commit, patch, or release-note URL>
- Trigger provenance: <PoC or regression-test URL and author>
- Software sources and pins: <package attribute or upstream artifact, version,
  revision, URL, and integrity hash for each variant>
- Local adaptations: <what changed and which security-relevant action stayed>

## Limitations and safety

State verified limits and the VM or container isolation boundary. Use
"None known" only when that is accurate.

## Reproduction metadata

- Reproduced by: <person or LLM agent>
- Date: <YYYY-MM-DD>

### LLM-only metadata (only if an LLM agent performed this work)

- Model: <runtime-exposed model or not available (not exposed by harness)>
- Agent harness: <runtime-exposed harness or not available (not exposed by harness)>
- User shell: <shell or not available (not exposed by harness)>
- Command-runner shell: <shell>
- UTC start: <YYYY-MM-DD HH:MM:SS UTC>
- UTC end: <YYYY-MM-DD HH:MM:SS UTC>
- Elapsed time: <duration or not available (not exposed by harness)>
- Input tokens: <count or not available (not exposed by harness)>
- Output tokens: <count or not available (not exposed by harness)>
- Total tokens: <count or not available (not exposed by harness)>
- Cost: <amount or not available (not exposed by harness)>
- Telemetry source: <harness source or not available (not exposed by harness)>
````

For LLM reproduction metadata, follow the
[case reporting skill](../agents/skills/case-reporting/SKILL.md#report-verified-evidence).

**Previous:** [Step 8: Verify test correctness](./08-verify-test.md) · **Next:** [Workflow overview](../reporting-vulnerabilities.md)
