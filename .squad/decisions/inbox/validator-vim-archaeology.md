### 2026-07-31: Validator-4 Nixpkgs Archaeology — Vim 8.1.1364/1365

**TL;DR:** The exact versions **vim 8.1.1364 and 8.1.1365 were NEVER packaged in
NixOS/nixpkgs**. Nixpkgs jumped straight from **8.1.1234 → 8.1.1432** in a single
commit on 2019-06-03, stepping right over the CVE-2019-12735 fix boundary
(fixed upstream in 8.1.1365). Substitute pins on either side of that boundary are
available and fully corroborated (see below).

---

**Search methodology:**

- GitHub REST API `code search` for `8.1.1364` / `8.1.1365` in `repo:NixOS/nixpkgs`
  → returned HTTP 401 (unauthenticated code search is not permitted; not usable).
- **Authoritative approach used instead — commit history of the vim version file**
  `pkgs/applications/editors/vim/common.nix` (the file that pins vim's `version`
  and source hash). Queried the GitHub commits API filtered by `path=` for the
  whole of 2019. This is the single source of truth for what vim version nixpkgs
  master shipped at any given time.
  - `GET /repos/NixOS/nixpkgs/commits?path=pkgs/applications/editors/vim/common.nix&since=2019-01-01&until=2019-12-31&per_page=100`
- Cross-checked commit messages (each bump states `old -> new` explicitly) and
  the numirias advisory / upstream fix version already recorded in the case readme.

**Full nixpkgs vim version timeline for 2019 (from common.nix history):**

| Commit (SHA) | Date (author) | Version change |
|---|---|---|
| `94169b166667723f250808420b1ae56a8cf58c01` | 2019-04-07 | 8.1.0578 → 8.1.0675 |
| `a529bc7f596e808ad612d2a7f50de297d8681978` | 2019-05-02 | 8.1.0675 → **8.1.1234** |
| `30496d80fabe3cdf84267e0e545c952c416b19cf` | 2019-06-03 | **8.1.1234 → 8.1.1432** ← crosses the fix boundary |
| `2b974b576c6ed8b32316f803e82635203b2177ba` | 2019-06-18 | 8.1.1432 → 8.1.1547 |
| `42607bb05904dbd05895cc584401a714ca71a3f3` | 2019-09-03 | 8.1.1547 → 8.1.1967 |
| `bacc6dcd5612a603d17f51dc77c1f6ada05e85cb` | 2019-10-24 | 8.1.1967 → 8.1.2188 |
| `02c3bcee61b6bbe61f34b043c1b511776039ed00` | 2019-11-03 | 8.1.2188 → 8.1.2237 |
| `f45df9cd4761131ea1ce2179832f8bb7c090f53a` | 2019-12-10 | 8.1.2237 → 8.1.2407 |

CVE-2019-12735 is fixed in vim **8.1.1365** (upstream patch, June 2019). The fix
boundary (1364 vulnerable → 1365 fixed) falls *inside* the 8.1.1234 → 8.1.1432
jump, so nixpkgs has exactly one vulnerable pin (8.1.1234) and one fixed pin
(8.1.1432) bracketing it — but neither exact number requested.

---

**Findings:**

#### Vim 8.1.1364 (requested vulnerable variant)
- Nixpkgs commit: **NOT FOUND — 8.1.1364 was never packaged in nixpkgs.**
- **Recommended substitute (vulnerable):** nixpkgs commit
  **`a529bc7f596e808ad612d2a7f50de297d8681978`** → ships **vim 8.1.1234**.
  - URL: `https://github.com/NixOS/nixpkgs/archive/a529bc7f596e808ad612d2a7f50de297d8681978.tar.gz`
  - Timestamp: 2019-05-02T23:52:13Z (author=committer: R. RyanTM / r-ryantm bot)
  - Why valid: 8.1.1234 < 8.1.1365 ⇒ vulnerable to modeline RCE. Falls squarely
    inside the case's stated "vim 8.1.0–8.1.1364" vulnerable range.
  - Corroboration: **HIGH** — version stated verbatim in the commit message
    (`vim: 8.1.0675 -> 8.1.1234`) and it is the parent state of the 1432 bump.

#### Vim 8.1.1365 (requested fixed variant)
- Nixpkgs commit: **NOT FOUND — 8.1.1365 was never packaged in nixpkgs.**
- **Recommended substitute (fixed):** nixpkgs commit
  **`30496d80fabe3cdf84267e0e545c952c416b19cf`** → ships **vim 8.1.1432**.
  - URL: `https://github.com/NixOS/nixpkgs/archive/30496d80fabe3cdf84267e0e545c952c416b19cf.tar.gz`
  - Timestamp: 2019-06-03T08:04:55Z (author=committer: R. RyanTM / r-ryantm bot)
  - Why valid: 8.1.1432 ≥ 8.1.1365 ⇒ contains the CVE-2019-12735 modeline fix.
    It is the first nixpkgs revision on/after the fix.
  - Corroboration: **HIGH** — version stated verbatim in the commit message
    (`vim: 8.1.1234 -> 8.1.1432`).

---

**Conclusion:**

- Exact requested pins (8.1.1364 / 8.1.1365): **Commits not in public history —
  nixpkgs never packaged either exact patch level.** Validator-3's block was
  correct: NixHub cannot expose them because they do not exist in nixpkgs.
- **Both bracketing substitute commits ARE found and HIGH-corroborated.** The case
  can proceed with a minor redesign of the version labels:
  - Vulnerable pin → `a529bc7f596e808ad612d2a7f50de297d8681978` (vim 8.1.1234)
  - Fixed pin      → `30496d80fabe3cdf84267e0e545c952c416b19cf` (vim 8.1.1432)
- This is the recommended path. It keeps the case nixpkgs-native (matches the
  existing `builtins.fetchTarball` strategy in `vm-server.nix`) and needs no
  custom vim source derivation. **"Ready for vm-server.nix pin update + sha256
  computation (deferred to later session with bash available)."**

**Next steps:**

1. Update `cves/cve-2019-12735-vim-modeline-rce/vm-server.nix`:
   - `vulnerableVimInfo.url` → the `a529bc7f…` archive URL above.
   - `fixedVimInfo.url` → the `30496d80…` archive URL above.
2. **Deferred to a session with bash / nix:** compute the two `sha256` values with
   `nix-prefetch-url --unpack <url>` (or `nix flake prefetch` / `nix-prefetch-github
   NixOS nixpkgs --rev <sha>`), and drop them into `vulnerableVimInfo.sha256` /
   `fixedVimInfo.sha256`.
3. Update the readme/case labels to reflect the real pinned versions
   (vulnerable = 8.1.1234, fixed = 8.1.1432) instead of the non-existent
   1364/1365, and note the substitution rationale. The `/etc/nice-archive/
   cve-2019-12735-vim-version` marker already reports `vimPkg.version` at runtime,
   so the oracle/version reporting stays accurate automatically.
4. Optional (only if an *exact* 8.1.1364 vs 8.1.1365 diff is ever mandated): build
   vim from the upstream `vim/vim` tags `v8.1.1364` / `v8.1.1365` via a small
   `stdenv.mkDerivation` / `fetchFromGitHub` override instead of a nixpkgs archive
   pin. Not recommended unless required — heavier and unnecessary for the oracle,
   since the marker-file oracle only needs one vulnerable and one fixed build.

**Corroboration / evidence level:** HIGH for both substitute commits (versions are
stated verbatim in the nixpkgs commit messages, and the two commits are direct
parent/child neighbours in the `common.nix` history straddling the fix). No commit
SHA, version range, or URL in this report was guessed — all were read directly from
the GitHub commits API for `pkgs/applications/editors/vim/common.nix`.

**Known limitations:**
- sha256 hashes NOT computed this session (no bash / nix / nix-prefetch-url
  available; every `bash` invocation failed to start a shell process).
- Buildability of the 2019-05-02 nixpkgs pin on a modern host is unverified and may
  require `nixpkgs-unstable`-era Nix quirks; confirm at build time.
- GitHub unauthenticated *code* search (401) could not be used; findings rest on the
  *commit* history API, which is the authoritative source for pinned versions anyway.

**References:**
- Nixpkgs common.nix history (commits API), 2019 window — source of every SHA above.
- Vulnerable pin: https://github.com/NixOS/nixpkgs/commit/a529bc7f596e808ad612d2a7f50de297d8681978
- Fixed pin: https://github.com/NixOS/nixpkgs/commit/30496d80fabe3cdf84267e0e545c952c416b19cf
- Upstream fix (already in case readme): vim 8.1.1365,
  https://github.com/vim/vim/commit/53575521406739cf20bbe4e384d88e7dca11f040
- Advisory: https://github.com/numirias/security/blob/master/vim_neovim.md
