# Build upstream software and third-party packages

Use this when the [historical nixpkgs search](./02-research-and-sources.md)
finds no suitable package, or a trigger needs building. Build upstream and
registry software **with Nix**, using the project's language ecosystem builder.

## Contents

- [Common rules](#common-rules)
- [JavaScript and TypeScript: npm](#javascript-and-typescript-npm)
- [Python](#python-pypi-source-or-upstream-repository)
- [Bash](#bash-case-owned-shell-trigger)
- [Go](#go-modules)
- [Rust](#rust-cargo)
- [Java and Kotlin: Maven](#java-and-kotlin-maven)
- [Java and Kotlin: Gradle](#java-and-kotlin-gradle)
- [C and C++](#c-and-c-make-autotools-cmake)
- [PHP](#php-composer)
- [Ruby](#ruby-bundler-and-gems)

## Common rules

- Fetch each complete affected and fixed upstream source with a verified hash.
  Pin dependencies with its lockfile and the builder's hash or explicit
  dependency set. Record the source and fallback reason in the case README.
- Never copy affected-product source, manifests, or lockfiles into the case.
  Keep complex Nix expressions under `package/`.
- Keep case-owned trigger source under `exploit/<role>/`. Where a snippet uses
  `src = source;`, substitute that role directory and its own dependency pin.
  Install it only in the consuming VM; keep the oracle in `test.py`.
- Build through Nix's sandbox. Run targets and triggers only inside the lab VM.

For a two-variant target, select the input once in a packaging expression:

```nix
# package/target.nix (source selection; replace the final attrset with a builder)
{ pkgs, isVulnerable }:
let
  selected = if isVulnerable then {
    version = "<affected-version>";
    rev = "<affected-commit>";
    sourceHash = "sha256-<affected-source-hash>";
    depsHash = "sha256-<affected-dependency-hash>";
  } else {
    version = "<fixed-version>";
    rev = "<fixed-commit>";
    sourceHash = "sha256-<fixed-source-hash>";
    depsHash = "sha256-<fixed-dependency-hash>";
  };
  source = pkgs.fetchFromGitHub {
    owner = "<owner>";
    repo = "<repo>";
    inherit (selected) rev;
    hash = selected.sourceHash;
  };
in { inherit selected source; }
```

The fragments below use these variables. Replace placeholders, check the
builder API in the pinned nixpkgs revision, and use `pkgs.fetchurl` for a
hashed registry tarball.

## JavaScript and TypeScript: npm

Requires upstream `package.json` and `package-lock.json`:

```nix
pkgs.buildNpmPackage {
  pname = "<project>";
  inherit (selected) version;
  src = source;
  npmDepsHash = selected.depsHash;
}
```

Use `dontNpmBuild = true` if there is no build script.
[Case example: Vite `buildNpmPackage`](../../cves/cve-2025-31125-vite-fs-denied-bypass/vm-server.nix).
[Nixpkgs npm guide](https://nixos.org/manual/nixpkgs/unstable/#javascript-tool-specific)

## Python: PyPI source or upstream repository

Use `buildPythonPackage` for a library. Package missing dependencies with
fixed sources; do not fetch them through `pip` during the build.

```nix
pkgs.python3Packages.buildPythonApplication {
  pname = "<project>";
  inherit (selected) version;
  src = source; # or pkgs.fetchPypi with the exact sdist hash
  pyproject = true;
  build-system = [ pkgs.python3Packages.setuptools ];
  dependencies = [ pkgs.python3Packages.requests ]; # replace with actual deps
}
```

For a short trigger, install Python and its modules in the consuming VM.
[Case example: PyYAML `buildPythonPackage`](../../cves/cve-2020-14343-pyyaml-full-loader-rce/vm-server.nix).
[Nixpkgs Python guide](https://nixos.org/manual/nixpkgs/unstable/#python)

## Bash: case-owned shell trigger

Declare runtime commands in a Nix wrapper:

```nix
pkgs.writeShellApplication {
  name = "case-trigger";
  runtimeInputs = [ pkgs.curl pkgs.coreutils ];
  text = builtins.readFile ./exploit/attacker/trigger.sh;
}
```

The path assumes a case-root Nix file. `writeShellApplication` checks syntax
and enables strict Bash options. For an upstream shell target, fetch its source
and install its entry point with `stdenv.mkDerivation`.
[Nixpkgs shell helper](https://nixos.org/manual/nixpkgs/unstable/#trivial-builder-writeShellApplication)

## Go: modules

```nix
pkgs.buildGoModule {
  pname = "<project>";
  inherit (selected) version;
  src = source;
  vendorHash = selected.depsHash;
}
```

Use `vendorHash = null` only for a complete upstream vendor tree.
[Case examples: imagemeta target](../../cves/cve-2025-32024-imagemeta-exif-dos/vm-server.nix),
[Notation OCSP helper](../../cves/cve-2024-56138-notation-go-tsa-revocation/vm-attacker.nix).
[Nixpkgs Go guide](https://nixos.org/manual/nixpkgs/unstable/#sec-language-go)

## Rust: Cargo

```nix
pkgs.rustPlatform.buildRustPackage {
  pname = "<project>";
  inherit (selected) version;
  src = source;
  cargoHash = selected.depsHash;
}
```

Requires `Cargo.lock`; pin Git crates with output hashes when needed.
[Nixpkgs Rust guide](https://nixos.org/manual/nixpkgs/unstable/#compiling-rust-applications-with-cargo)

## Java and Kotlin: Maven

```nix
pkgs.maven.buildMavenPackage {
  pname = "<project>";
  inherit (selected) version;
  src = source;
  mvnHash = selected.depsHash;
  installPhase = ''
    runHook preInstall
    mkdir -p $out/share/java
    install -Dm644 target/<artifact>.jar $out/share/java/<project>.jar
    runHook postInstall
  '';
}
```

Replace the artifact path; add a `java -jar` wrapper if needed.
[Nixpkgs Maven guide](https://nixos.org/manual/nixpkgs/unstable/#maven)

## Java and Kotlin: Gradle

Gradle uses a dependency cache. Keep generated cache metadata under
`package/`, with separate files when variant dependencies differ.

```nix
pkgs.stdenv.mkDerivation (finalAttrs: {
  pname = "<project>";
  inherit (selected) version;
  src = source;
  nativeBuildInputs = [ pkgs.gradle ];
  mitmCache = pkgs.gradle.fetchDeps {
    pkg = finalAttrs.finalPackage;
    data = if isVulnerable
      then ./gradle-deps-vulnerable.json
      else ./gradle-deps-fixed.json;
  };
  installPhase = ''
    runHook preInstall
    mkdir -p $out/share/java
    install -Dm644 build/libs/<artifact>.jar $out/share/java/<project>.jar
    runHook postInstall
  '';
})
```

Check this cache API against the pinned nixpkgs revision.
[Nixpkgs Gradle guide](https://nixos.org/manual/nixpkgs/unstable/#gradle)

## C and C++: Make, Autotools, CMake

Use `stdenv.mkDerivation` for Make or Autotools; add CMake and Ninja only when
upstream uses them:

```nix
pkgs.stdenv.mkDerivation {
  pname = "<project>";
  inherit (selected) version;
  src = source;
  nativeBuildInputs = [ pkgs.cmake pkgs.ninja ];
  buildInputs = [ pkgs.openssl ]; # replace with actual libraries
}
```

For a case-owned C/C++ trigger:

```nix
pkgs.stdenv.mkDerivation {
  pname = "case-trigger";
  version = "1";
  src = ./exploit/attacker/c;
  dontConfigure = true;
  buildPhase = ''
    runHook preBuild
    cc trigger.c -o case-trigger
    runHook postBuild
  '';
  installPhase = ''
    runHook preInstall
    install -Dm755 case-trigger $out/bin/case-trigger
    runHook postInstall
  '';
}
```

[Case examples: CryptoLib CMake target](../../cves/cve-2025-29912-cryptolib-tc-underflow/cryptolib.nix),
[PwnKit C trigger](../../cves/cve-2021-4034-pwnkit/vm-server.nix).
[Nixpkgs CMake guide](https://nixos.org/manual/nixpkgs/unstable/#cmake)

## PHP: Composer

```nix
pkgs.php.buildComposerProject2 {
  pname = "<project>";
  inherit (selected) version;
  src = source;
  vendorHash = selected.depsHash;
}
```

Requires upstream `composer.json` and `composer.lock`. A short PHP trigger
may need only `pkgs.php` in its VM.
[Nixpkgs Composer guide](https://nixos.org/manual/nixpkgs/unstable/#php)

## Ruby: Bundler and gems

For a case-owned Ruby trigger, keep `Gemfile`, `Gemfile.lock`, `gemset.nix`,
and its script under the consuming role:

```nix
pkgs.bundlerApp {
  pname = "case-trigger";
  gemdir = ./exploit/attacker/ruby;
  exes = [ "case-trigger" ];
}
```

For an upstream Ruby target with `Gemfile` and `Gemfile.lock`, fetch the full
source and keep only generated gemset metadata under `package/`:

```nix
pkgs.bundlerApp {
  pname = "<project>";
  gemdir = source;
  gemset = if isVulnerable
    then ./ruby-gemset-vulnerable.nix
    else ./ruby-gemset-fixed.nix;
  exes = [ "<command>" ];
}
```

[Nixpkgs Ruby guide](https://nixos.org/manual/nixpkgs/unstable/#ruby)
