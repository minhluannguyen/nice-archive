# Contributing to NICE Archive

Thank you for your interest in contributing to NICE Archive!

We welcome new vulnerability recipes, improvements to existing recipes, bug fixes, enhancements to the framework and tools, and documentation contributions.

## Contributing a new CVE recipe

Because NICE Archive deals with security vulnerabilities, new recipes must meet the following requirements:

- **Public vulnerabilities only.** Recipes must target publicly disclosed CVEs. Zero-days, unpublished, and embargoed vulnerabilities are not accepted through public contributions.
- **Exploit provenance.** Clearly identify the source, author, license, and any modifications to the exploit or proof of concept (PoC). See our [Licensing Policy](./LICENSING.md).
- **Safe reproduction.** Exploitation must take place in isolated, controlled environments and must not target unauthorized systems.
- **Working reproduction.** Recipes must include functional validation tests and a way to debug the environment, either through scenario mode or standalone VMs.

To create a recipe, follow the [documentation](./docs/README.md) and refer to existing CVE cases for examples.
Maintainers use the [new recipe review guide](./docs/REVIEWING.md) for pull
requests that add a CVE recipe.

If you have an unpublished vulnerability, please contact upstream maintainers of the affected software to report the issue. If you are a software maintainer and wish to contribute a recipe for your own software, please contact the NICE Archive maintainers to discuss the best way to do so.

## Other contributions

We also welcome contributions that improve the archive itself, including:

- **Framework and tools:** Bug fixes and improvements to the CLI, helper libraries, and supporting tools.
- **Existing recipes:** Fixes, compatibility improvements, better tests, and documentation updates.
- **Documentation:** Corrections, tutorials, and examples.

For these contributions, follow the relevant [project documentation](./docs/README.md), test your changes where applicable, and describe their purpose in your pull request.

Changes to existing recipes that introduce new exploit material must also follow the exploit provenance and safety requirements above.

## Responsible AI use

AI-assisted contributions are welcome. However, contributors remain responsible for their submissions and must:

- Review and validate AI-generated content.
- Disclose substantial AI assistance in the pull request.
- Ensure generated code respects third-party licensing and attribution.
- Avoid sharing confidential or unpublished vulnerability information with external AI services without authorization.

## How to contribute

1. Check for existing issues or contributions addressing the same topic.
2. Clone or fork the repository and create a new branch for your changes.
3. Follow the [documentation](./docs/README.md) to create a new NICE recipe.
4. Open a pull request describing your contribution, its sources, and validation results.

All contributions are subject to maintainer review. We may request additional
evidence or changes before merging.

Thank you for helping make vulnerability research more reproducible and accessible!
