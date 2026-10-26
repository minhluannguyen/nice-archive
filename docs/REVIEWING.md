# Reviewing New CVE Recipes

Use this checklist for pull requests that add a new CVE recipe to NICE Archive.
For technical details, see [Reporting a Vulnerability](./reporting-vulnerabilities.md).

## 1. Review checklist

### Vulnerability and reproduction
- [ ] The CVE, affected software, and vulnerable/fixed versions are correct.
- [ ] The recipe reproduces the actual vulnerability with a valid exploit or trigger.
- [ ] The Nix/NixOS environment is correctly configured and reproducible.
- [ ] The recipe uses the NICE helper library where applicable. If not, the reason is documented.

### Testing and debugging
- [ ] The recipe provides a working automated test.
- [ ] Test assertions verify the vulnerability's security impact, not merely successful execution.
- [ ] Vulnerable and fixed versions exhibit the expected behaviors.
- [ ] A working debugging method is available, either through **scenario mode** or **standalone VMs**.

### Documentation and provenance
- [ ] The README clearly explains the vulnerability, setup, exploitation, and expected results.
- [ ] External PoCs and third-party code are properly attributed, including their sources and licenses.
- [ ] Limitations, assumptions, and deviations from the original vulnerability are documented.

### Review validation
- [ ] The reviewer has inspected the recipe and verified its correctness, not relying solely on automated evaluation.
- [ ] The tests have been independently executed, or missing validation is explicitly recorded.
- [ ] Any remaining concerns are documented and appropriately labeled.

## 2. Flagging difficult cases

Apply `type:new-recipe` to pull requests that add a CVE recipe.

Apply relevant labels to identify recipes requiring extra attention:

| Label | Description |
|---|---|
| `difficult-reproduce:flaky` | Inconsistent or nondeterministic reproduction |
| `difficult-reproduce:environment` | Complex dependencies or environment requirements |
| `difficult-reproduce:manual` | Requires manual interaction |
| `difficult-review:vuln-in-lib` | Vulnerability resides in a library |
| `difficult-review:complex-poc` | Exploit is difficult to understand or verify |
| `difficult-review:unclear-assertion` | Test assertions do not clearly establish the vulnerability |
| `difficult-review:partial-reproduction` | Only part of the vulnerability is demonstrated |

For flagged cases, briefly explain the concern and any required action in the PR.

These labels do not automatically block merging, but concerns must be reviewed before acceptance.

## 3. Review decision

- **`review:ready`** — Requirements satisfied; ready to merge.
- **`review:needs-changes`** — Corrections required before merging.
- **`review:needs-validation`** — Additional verification required.

Do not merge recipes with unresolved correctness, reproducibility, or security concerns. Accepted limitations must be clearly documented.
