# Blocker — Nixpkgs Hashes for Batch 1 CVEs

**Date**: 2026-07-31  
**Status**: ⚠️ REQUIRES TEAM DECISION

## Issue

Batch 1 needs nixpkgs commit pins for vulnerable/fixed package versions, but public `sha256` discovery is incomplete.

### 1. CVE-2022-35252 (curl 7.85.0+)

- **Commit(s)**: TBD — exact nixpkgs commits for vulnerable/fixed curl versions still need pinning
- **Status**: Requires nix-versions.com lookup and likely local `nix-prefetch-url`
- **Blocker**: Unknown which relevant commits have publicly documented hash records

### 2. CVE-2019-12735 (vim 8.1.1365+)

- **Commit(s)**: TBD — vim version pinning not yet finalized
- **Status**: Requires nix-versions.com lookup and likely local `nix-prefetch-url`
- **Blocker**: Unknown which relevant commits have publicly documented hash records

### 3. CVE-2018-25032 (zlib 1.2.12)

- **Commit(s)**: TBD — zlib version pinning not yet finalized
- **Status**: Requires nix-versions.com lookup and likely local `nix-prefetch-url`
- **Blocker**: Unknown which relevant commits have publicly documented hash records

## Team Options

### Option 1: Manual Verification

- Run:

```bash
nix-prefetch-url --unpack "https://github.com/NixOS/nixpkgs/archive/{COMMIT}.tar.gz"
```

- Record the returned hash in `vm-server.nix`
- Best option for strict reproducibility

### Option 2: Dynamic Hash Fetch

- Leave the hash unresolved until first build/import
- Faster iteration, weaker up-front reproducibility guarantees

### Option 3: Reuse Existing Public Hashes

- Use publicly corroborated hashes when available
- Continue searching `nix-versions.com`, public flakes, and repo history before falling back to local prefetch

## Recommendation

Proceed with **Option 1** once exact nixpkgs commits are known for each case. That gives the cleanest audit trail and avoids silent pin drift.

## Unlock Path

1. Pin exact nixpkgs commits for:
   - curl 7.85.0 boundary
   - vim 8.1.1365 boundary
   - zlib 1.2.12 boundary
2. Run `nix-prefetch-url --unpack` for each chosen commit
3. Update `vm-server.nix` pins with computed hashes
4. Rebuild and run the case through NICE Archive

---

**Blocker owner**: Validator  
**Requires**: Team decision on reproducibility vs effort trade-off
