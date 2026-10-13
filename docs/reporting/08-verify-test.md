# 8. Verify test correctness

Check that the automated test proves the same security effect observed in
scenario mode. Review the test before running it:

1. Confirm the evaluated target versions and pins match the researched
   vulnerable and fixed selections.
2. Confirm both branches run the same bounded trigger from the intended VM.
3. Check that the vulnerable branch asserts the target-specific effect at the
   correct trust boundary, using evidence observed in scenario mode.
4. Check that the fixed branch asserts the effect is absent and the target
   still handles a normal operation.
5. Check guest waits, commands, and network calls have finite timeouts, and
   that an applicable assertion helper completes each branch.

Run both complete variants through the CLI and inspect their logs:

```bash
nice-archive test --case cve-yyyy-nnnn-short-name --vulnerable true --log live
nice-archive test --case cve-yyyy-nnnn-short-name --vulnerable false --log file
git status --short
```

The [CLI guide](../cli-tool.md) defines options and log locations. A passing
test command proves only that its assertions passed; compare the logged guest
evidence with the manual observations and the intended security effect. A
failed build, timeout, killed process, or unverified version is a failure or
blocker, not a passing variant. Record exactly which commands ran and what
each proved.

Complete tests, scenarios, guest waits, and network triggers need finite
deadlines. Review staged files and remove generated artifacts before finishing.

**Previous:** [Step 7: Write the automated test](./07-test.md) · **Next:** [Step 9: Write the case README](./09-case-readme.md)
