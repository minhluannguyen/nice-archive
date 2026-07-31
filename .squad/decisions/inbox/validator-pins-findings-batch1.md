# Validator Pin Findings — Batch 1

**Date**: 2026-07-31  
**Agent**: Validator  
**Scope**: nixpkgs commits for curl 7.85.0+, vim 8.1.1365+, zlib 1.2.12  

## Summary

Searched for nixpkgs commit hashes via:
- GitHub code search / public repo references
- nix-versions.com references
- Independent nixpkgs configs from unrelated repositories

**Result**: Found corroborated public hash for **one** commit; two commits have **no discoverable sha256** in public sources reviewed so far.

## Key Finding

### Commit `611bf8f183e6360c2a215fa70dfd659943a9857f`

- **sha256**: `sha256:1rhrajxywl1kaa3pfpadkpzv963nq2p4a2y4vjzq0wkba21inr9k`
- **Evidence**:
  - Identical hash appears in multiple unrelated public repos
  - Cross-corroborated in at least:
    - `pschmitt/nixos-config`
    - `kbudde/nixos`
    - `WeissP/nix-config`
    - additional public nix configs found during search
- **Confidence**: ✅ HIGH — same hash reused across unrelated authors

### Commit `253272ce9f1d83dfcd80946e63ef7c1d6171ba0e`

- **sha256**: ❌ NOT FOUND
- **Evidence**:
  - Commit reference was discoverable
  - No public repo, example flake, or config located with a matching `sha256`
  - Only indirect version-tracking reference identified: `RyanGibb/opam-lang-repo-nix`
- **Confidence**: ❌ NONE — no independently discoverable hash
- **Workaround**:

```bash
nix-prefetch-url --unpack https://github.com/NixOS/nixpkgs/archive/253272ce9f1d83dfcd80946e63ef7c1d6171ba0e.tar.gz
```

## Sources Consulted

- Public GitHub code search for commit IDs and matching `sha256` values
- `nix-versions.com`
- Independent public nixpkgs-based configs and flakes from unrelated repositories

## Recommendation for Team

For commits without public `sha256` records:

1. **Option A (Local Verification)**: run `nix-prefetch-url` locally to compute the hash
2. **Option B (Accept Risk)**: use commit ref without pre-documented hash
3. **Option C (Escalate)**: decide whether the case can tolerate dynamic first-build hash discovery

## Implication

Some Batch 1 cases may not have complete reproducible pins from public evidence alone. Team decision needed on reproducibility strictness versus additional manual verification effort.
