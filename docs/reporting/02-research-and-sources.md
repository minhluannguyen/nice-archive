# 2. Research the vulnerability and select software

Record the affected software, authoritative version range, required
preconditions, security effect, fixing change, and a testable difference
between vulnerable and fixed behavior. Reconcile the CNA or NVD record with
upstream advisories, fixes, release notes, regression tests, and distribution
advisories. Resolve disagreements before selecting versions. A vulnerable
selection may be any release proven inside the affected range; it need not be
the last affected release.

Choose a trigger from a supplied or public PoC or an upstream regression test
when available. Preserve its security-relevant action. Record its source,
author, adaptations, and bounds. If no suitable trigger exists, derive a
minimal one from the authoritative advisory or fix. Keep vulnerable/fixed
expectations in `test.py`, rather than making the trigger declare itself a
success or failure.

## Select the target source

Search historical nixpkgs before building from source. A practical order is:

1. Select vulnerable and fixed packages from pinned nixpkgs revisions and
   change only the affected package in the target VM.
2. If the software needs matching system components, pin the target's entire
   NixOS system separately for each variant.
3. Use old-kernel support when the required kernel or old NixOS environment
   cannot be represented by the earlier approaches.
4. As a fallback, let Nix fetch and build a complete immutable upstream
   release, tag, commit, or registry package with a verified hash.

## Find a historical package version

Start with [nixpkgs-multiverse](https://github.com/fzakaria/nixpkgs-multiverse),
which indexes package attributes and the nixpkgs revisions that shipped them.
The examples below use `curl` and `python3` to explain the search process;
select versions for an actual case from that CVE's authoritative affected
range and fix evidence.

First, find an attribute and ask when a candidate version was available:

```bash
nix run 'github:fzakaria/nixpkgs-multiverse#mvs' -- query search curl
nix run 'github:fzakaria/nixpkgs-multiverse#mvs' -- query versions curl
nix run 'github:fzakaria/nixpkgs-multiverse#mvs' -- query when curl 7.83.0
```

`search` helps when the package attribute is unclear. `versions` lists indexed
versions; `when` shows the revision labels that contained the requested
version, including separate runs if it disappeared and returned. Pick a
candidate revision from that output.

For a concrete check of a revision, the multiverse documentation gives this
independent `python3` example. Ask what a date shipped, then resolve the
returned revision label to a full commit:

```bash
nix run 'github:fzakaria/nixpkgs-multiverse#mvs' -- query at 2022-03-15 python3
nix run 'github:fzakaria/nixpkgs-multiverse#mvs' -- query rev 2022-03-14-73ad5f9e147c
```

In this documented example, `query at` reports `python3` version `3.9.10`
and revision label `2022-03-14-73ad5f9e147c`. Resolving the label yields the
full commit `73ad5f9e147c0d2a2061f1d4bd91e05078dc0b58` for a stable pin.
For a CVE, use the revision label from *its* version search and repeat the
check for both selected variants. A release tag can move as backports arrive,
so pin the resolved commit rather than the tag.

Finally, evaluate the actual package version from the selected revision. This
step may fetch and evaluate that historical nixpkgs revision:

```bash
nix eval --raw 'github:fzakaria/nixpkgs-multiverse#2022-03-14-73ad5f9e147c.python3.version'
```

The index covers top-level attributes and selected nested sets. For a nested
attribute absent from the index, such as a particular
`python3Packages.requests` or `linuxPackages.kernel` selection, first choose
a revision and then evaluate the nested package at that revision. The
[multiverse CLI reference](https://github.com/fzakaria/nixpkgs-multiverse/blob/main/docs/cli.md)
documents `search`, `versions`, `when`, `at`, and `rev`; its
[Nix API reference](https://github.com/fzakaria/nixpkgs-multiverse/blob/main/docs/nix-api.md)
explains revision selectors.

If the index has no suitable result, try [`nix-versions`](https://github.com/denful/nix-versions)
to search other historical package indexes. It is available in this
repository's [development shell](../../README.md#development-shell):

```bash
nix-versions 'bin/curl@7.83'
```

Here `bin/curl` searches for the executable name, while `@7.83` filters
candidate versions. The [nix-versions usage guide](https://nix-versions.alwaysdata.net/getting-started/finding-packages/)
explains executable searches and its historical backends. Verify the full
version and revision returned by the chosen backend.

Treat search results as candidates, not as proof of an affected or fixed
release. Confirm the exact evaluated package version, package attribute,
full nixpkgs commit, source URL, and integrity hash for each selection. If
fetching a nixpkgs archive directly, calculate its hash with
`nix-prefetch-url <archive-url> --unpack`. The
[Heartbleed VM module](../../cves/cve-2014-0160-heartbleed/vm-server.nix)
illustrates package-level pinning; the [library reference](../nice-archive-libs.md#historical-package-pin-inside-a-vm)
explains how to use a historical package in a case. Keep package choice near
the target VM unless the whole-system pin must change.

Never copy, vendor, reconstruct, or reduce affected-product source in the
case. Case-owned VM modules, packaging expressions, wrappers, tests, and
trigger code are appropriate. Fetch upstream patches immutably with verified
hashes. The exact selection and acquisition source belong in the
[case README](./09-case-readme.md).

## Build complete upstream source when pins fail

When no suitable historical nixpkgs package exists, use the
[upstream and third-party package build guide](./upstream-and-third-party-builds.md).
It covers source and dependency pins, plus Nix examples for npm, Python, Bash,
Go, Rust, Maven, Gradle, C/C++, Composer, and Ruby. The same guide explains
how to package case-owned exploit helpers without putting affected-product
source in the case.

**Previous:** [Step 1: Create or find the case](./01-create-case.md) · **Next:** [Step 3: Design the topology and choose a generator](./03-design.md)
