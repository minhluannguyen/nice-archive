# 7. Write the automated test

Run `nice-archive begin-test-phase` before writing or refining the test after
manual validation. For attempts using a shared phase budget, this starts one
40-minute window for writing, both complete variants, and fixes. A test call
also starts it if the marker was missed.

Keep `test.py` linear: wait for readiness, execute the same bounded trigger
against both variants, collect evidence, then assert the vulnerable or fixed
result. VM names in the generator become Python variables in the NixOS test
driver. Put the expectation in `test.py`; the trigger should perform the
security-relevant action without deciding whether the case passed.

```python
import assertion_blocks as ab

start_all()
server.wait_for_unit("example.service", timeout=120)
status, output = attacker.execute("run-trigger server", timeout=30)

variant = server.succeed("cat /etc/nice-archive/variant", timeout=10).strip()
if variant == "vulnerable":
    ab.check_file_contains(server, "/tmp/effect", "NICE-CVE-YYYY-NNNN", timeout=60)
else:
    assert variant == "fixed"
    server.succeed("systemctl is-active example.service", timeout=30)
    ab.check_file_exists(server, "/tmp/effect", is_existing=False, timeout=60)
```

The VM module must create the variant file; the generator does not inject that
Python variable. The example's target-side file is appropriate only when it
proves the actual security effect. For disclosure, compare attacker-observed
data with a target-only value. For remote execution or privilege escalation,
check the unauthorized effect at the affected target. Avoid using command
success, exploit self-reporting, generic OS content, or output-file existence
alone as the oracle.

Wait only for the prerequisite the next step needs: a unit, port, file, or
application response. Use DNS and extra connection probes for a specific
communication dependency or diagnosis, not as a routine preamble. Reuse
trigger or oracle evidence that proves fixed-target health; add one bounded
benign check only when that evidence is insufficient.

Use concise phase comments and finish each branch with an applicable
`assertion_blocks` helper. Use a direct assertion only when no helper expresses
the security property, and explain that choice in the README. The
[library reference](../nice-archive-libs.md#python-assertion-blocks) lists
helpers, signatures, and attack-type examples; the
[NixOS test-driver reference](https://nixos.org/manual/nixos/stable/#ssec-machine-objects)
defines machine methods.

Set native `timeout=` values on guest commands and waits, plus connect and
read timeouts inside network triggers. A timeout or forced kill is a failure
or blocker, not proof of fixed behavior. Keep routine checks short enough to
leave time for both variants and fixes; allow measured service startup time.
Bound readiness checks, trigger
execution, and fixed-variant health checks separately. See
[vulnerability-specific guidance](../vulnerability-specific-reproduction.md)
for browser and resource-exhaustion oracles.

**Previous:** [Step 6: Use scenario mode to test exploitation](./06-scenario-mode.md) · **Next:** [Step 8: Verify test correctness](./08-verify-test.md)
