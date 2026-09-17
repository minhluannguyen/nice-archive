# otool: CVE OpenCode batch orchestrator

`cve-orchestrator` runs one OpenCode agent job per CVE. By default each job,
including recipe evaluation, runs in its own ephemeral OpenStack VM. A
`--execution-backend local` compatibility mode retains the standalone repository
copy behavior. It supports parallel workers, selective infrastructure retries,
hard attempt/token/call budgets, resume, per-CVE cleanup, live
interaction output, optional independent LLM evaluation, random human-review
sampling, and optional OpenRouter metadata enrichment.

Dry-run checks are grouped under one option:

- `--dry-run` or `--dry-run ui` exercises the real terminal UI for 30 seconds
  with gradually increasing synthetic worker, resource, and token counters. It
  makes no external calls, consumes no model tokens, and writes no artifacts.
- `--dry-run openstack` creates one real OpenStack keypair and VM per active
  worker, injects the public key, verifies SSH, runs the same 30-second
  token-free simulation, and then deletes the resources.
- `--dry-run metadata` runs one harmless fake-CVE prompt through OpenCode to
  verify metadata collection. Unlike the other modes, this makes a small model
  call and writes the normal probe result artifacts.

UI mode uses CVEs from the supplied list or synthetic CVE labels when no list
is supplied:

```bash
cve-orchestrator --dry-run --workers 2
cve-orchestrator cves.txt --dry-run ui --workers 3
```

The UI is enabled automatically for a dry run unless `--no-live` is supplied.

Use OpenStack mode to exercise the real cloud lifecycle without invoking
OpenCode or a model provider:

```bash
cve-orchestrator cves.txt \
  --dry-run openstack \
  --workers 2
```

This opt-in mode creates billable cloud resources and can take longer than 30
seconds overall because provisioning, SSH readiness, and deletion happen
outside the timed UI simulation. It still consumes zero model tokens.

Implementation, helper modules, prompts, and Nix packaging live under `otool/`.
The repository-root `./cve-orchestrator` Bash launcher remains the entry point.
Bundled prompts are resolved relative to this tool directory, independently of
the working directory or `--repo`. Existing result locations and legacy
workspace-related CLI names and overrides are unchanged.

```text
otool/
├── cve-orchestrator.py
├── readme_metadata.py
├── recipe_evaluation_report.py
├── package.nix
├── README.md
└── docs/
    ├── cve-recipe-evaluator-prompt.md
    └── cve-readme-metadata-prompt.md
```

## What it records

For every attempt it records:

- wall-clock execution time
- OpenCode exit code / timeout state
- configured and observed live LLM-call/input-token budgets, including the
  exact exceeded limit when an attempt is stopped
- agent-declared reproduction result (`success`, `failure`, or `inconclusive`)
- orchestrator-generated fallback summary from logs and repository-copy state, even
  when the agent omits or corrupts `EXPERIMENT_RESULT.json`
- best-effort OpenCode input, output, reasoning, cache, total token, cost,
  model, LLM-call, and tool-call metadata from JSON events
- full OpenCode JSONL output and stderr
- a complete recipe copy under the canonical per-CVE `recipe/` directory, excluding
  generated VM images, logs, and other configured artifacts
- the raw `EXPERIMENT_RESULT.json` copied into each attempt directory
- an optional, separately validated evaluator verdict and its exact prompt,
  command, logs, metadata, artifact inventory, and JSON result
- OpenRouter prompt/completion/reasoning/cached token counts, provider, model, latency, and cost when an OpenRouter generation ID is available

The runner does not ask the LLM to estimate its own token use. Per-CVE
OpenRouter attribution is exact when OpenRouter `gen-...` IDs appear in
OpenCode output. Otherwise, sequential runs can still record an API-key spend
delta.

While jobs are running, the orchestrator shows one vertical block per worker:
CVE, attempt, elapsed time, logical step, active tool/command, the last ten
sanitized command-output lines, and live budget usage. The full raw streams are
still written to the attempt artifacts. Use `--live` to force concise
state-change output when stderr is not a TTY, or `--no-live` for quiet batch
logs. OpenCode stderr and provider-stall warnings remain visible and persisted
even with `--no-live`, so remote workers do not fail silently.

Inside either backend, the job uses a repository copy with its own `.git`
metadata so existing status/diff evidence collection continues to work. The
orchestrator does not create a branch or call `git worktree`.

The NICE Archive CLI serializes `nice-archive scenario` startup with a file
lock because concurrent scenario-mode VM labs can block each other. Local
workers share `NICE_ARCHIVE_SCENARIO_LOCK=<results-root>/.scenario.lock`.
OpenStack workers have independent hosts and locks, so their scenario/test
commands cannot contend for host QEMU or test-driver processes.

The bundled agent starts scenarios with `--popup false --log file
<variant>.log --status-file <variant>.status.json`. File mode keeps the full
test-driver transcript off the model-facing console and exposes a bounded
`scenario> ` proxy instead. The agent sends one-line Python commands through
the managed PTY, uses `exec("...\\n...")` for multi-line Python, reads through
the `</scenario-command-output>` marker, and enters `:quit` before waiting for
the scenario process to exit. The status JSON supplies lifecycle state and
verified SSH commands without requiring repeated transcript reads.

## 1. Prepare the CVE list

```text
CVE-2023-50268
CVE-2019-10906
CVE-2021-23980
CVE-2024-23334
```

Blank lines and `#` comments are ignored.

## 2. Execution backends

`openstack` is the default. The orchestrator parses (but does not execute)
`app-cred-nice-llm-reproduction-cred-openrc.sh`, creates a unique ephemeral
Ed25519 OpenStack keypair and one VM per CVE, injects the public key through
`server create --key-name`, waits for SSH, and transfers a credential-filtered
copy of the repository, then runs the ordinary local
orchestrator inside that VM. Reproduction, README metadata finalization, and
optional recipe evaluation all finish remotely. Result files are synchronized
to the host every 30 seconds and once more before the VM and keypair are
deleted. The OpenRC and generated private key are never uploaded.

Keep the credential host-readable only by its owner:

```bash
chmod 600 app-cred-nice-llm-reproduction-cred-openrc.sh
```

The orchestrator warns when group or other permission bits are present.

Selected defaults are `NixOS-26.05-custom`, `m2.large`, `provider`, the
`default` security group, and SSH user `root`. The requested image and flavor
were verified in the tenant; override the login account if the custom image
uses another user. Override settings with
`--openstack-image`, `--openstack-flavor`, `--openstack-network`,
`--openstack-security-group`, or `--openstack-ssh-user`. The selected image must
support OpenStack SSH-key injection, password SSH for fallback, a writable home
directory, `sudo` when the login is not root, outbound package downloads, and Nix.
The custom NixOS image is expected to provide working `nix`, flakes, `rsync`,
and any required nested-KVM configuration. The orchestrator does not install or
configure Nix inside the VM.

Pass `--debug` to save a detailed host-side trace for each VM. Normal runs write
`CVE-.../infrastructure/vm-debug.log`; OpenStack dry runs write beneath
`<results>/openstack-dry-run/<server-name>/vm-debug.log`. The trace includes
OpenStack commands and responses, SSH readiness attempts, SCP/rsync actions,
remote commands and output, and lifecycle cleanup or retention events. Secret
environment values are not included, and recognizable credential forms are
redacted.

The custom image is currently registered in Glance with `disk_format=iso`.
SSH-key injection and writable-root behavior depend on how that ISO was built
and should be confirmed with a one-VM provisioning smoke test.

The generated public key is injected during OpenStack server creation. SSH
readiness checks prefer that key and fall back to the custom image's default
password, `nixos`, including keyboard-interactive authentication. Subsequent
SSH, SCP, and rsync operations use the injected key only.
Password delivery uses `sshpass -e`,
so it does not appear in the SSH/SCP command arguments or logs. Set
`OPENSTACK_SSH_PASSWORD` in the host environment or `.env` to override it.
Set an empty value to disable password fallback and use only the injected key.
This value is removed from the filtered `.env` uploaded to worker VMs.

The OpenStack backend requires `openstack`, `ssh`, `scp`, `sshpass`, `rsync`,
`tar`, and `ssh-keygen`; the flake supplies them. It performs a read-only image/flavor/
network/security-group preflight before creating anything. Infrastructure logs
and lifecycle metadata are written under each result's `infrastructure/`
directory. OpenStack usage may incur compute and network charges.

Cleanup targets the exact server UUID returned by creation. If final sync or
deletion fails, `state.json` reports `orchestrator_error` and
`infrastructure/openstack.json` retains the server UUID and error instead of
claiming cleanup succeeded. After inspecting the failure, an administrator can
remove that exact resource with `openstack server delete <server-id>`.

Pass `--openstack-keep-vm` to retain each VM and OpenStack keypair after the
final artifact synchronization, including when a reproduction is interrupted:

```bash
cve-orchestrator cves.txt --openstack-keep-vm
```

An intentional retention is recorded as `retained: true` rather than a cleanup
failure. The matching private/public key is saved under
`CVE-.../infrastructure/ssh/` with private-key mode `0600`, and
`infrastructure/openstack.json` records the exact server UUID, keypair name,
address, and SSH command. OpenStack dry runs store retained-resource records
under `<results>/openstack-dry-run/<server-name>/`. Retained VMs continue to
incur cloud charges. After inspection, delete the exact server and keypair,
then remove the saved private key:

```bash
openstack server delete <server-id>
openstack keypair delete <keypair-name>
```

To retain the prior host execution behavior:

```bash
cve-orchestrator cves.txt --execution-backend local
```

## 3. OpenCode setup

Inside `nix develop`, use the packaged binary directly. Outside the dev shell,
prefix commands with `nix run .#cve-orchestrator --`.

The flake includes Nixpkgs' `opencode` package, which provides the `opencode`
binary used by default. The orchestrator loads simple `KEY=VALUE` entries from
the repository `.env` and passes that environment to `opencode run`, so provider
API keys can be stored there.

Every OpenCode invocation enables `--print-logs`: normal runs use OpenCode's
`INFO` log level and `--debug` runs use `DEBUG`. This makes provider connection,
authentication, request, and plugin diagnostics available in the per-attempt
`opencode-stderr.log` and the orchestrator's live output instead of leaving an
apparently silent process.

Prompts are never interpolated into a shell command or placed in OpenCode's
argument vector. The orchestrator writes the exact UTF-8 prompt to `prompt.md`
and supplies that file as the child process's standard input while launching
OpenCode with `shell=False`. This preserves quotes, backslashes, newlines, JSON,
and shell metacharacters verbatim and avoids command-line length limits.

The repository includes `.opencode/agents/cve-reproducer.md`. OpenCode 1.18.18
loads it as a primary agent with `steps: 40`; it also denies standalone
`sleep *` Bash commands while retaining Bash and all PTY tools. The agent uses
`pty_spawn(notifyOnExit=true)` for long jobs and waits for `<pty_exited>` rather
than polling. `.opencode/opencode.json` enables automatic compaction, old tool
output pruning, and a 20,000-token reserve. The orchestrator selects this agent
unless `--agent` or `OPENCODE_AGENT` selects another one. Unless the caller has
already set `OPENCODE_CONFIG_DIR`, it points OpenCode at this repository config
so the bundled agent is also available to resumed copies made by older runs.

Example `.env` entries:

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-v1-...

# Optional default model used when --model is omitted.
OPENCODE_MODEL=openai/<model-name>
# or:
OPENCODE_MODEL=anthropic/<model-name>
# or:
OPENCODE_MODEL=openrouter/deepseek/deepseek-v4-flash-0731

# Optional generator agent and reasoning variant.
OPENCODE_AGENT=cve-reproducer
OPENCODE_VARIANT=high

# Optional independent-review overrides. The model value includes its provider.
CVE_ORCHESTRATOR_EVALUATION_MODEL=anthropic/<reviewer-model>
CVE_ORCHESTRATOR_EVALUATION_AGENT=cve-reviewer
CVE_ORCHESTRATOR_EVALUATION_EFFORT=high

# Optional alternative to the OpenRC file. These stay on the host and are
# removed from the filtered .env uploaded to the worker VM.
OS_AUTH_URL=https://openstack.example/v3
OS_AUTH_TYPE=v3applicationcredential
OS_IDENTITY_API_VERSION=3
OS_REGION_NAME=RegionOne
OS_INTERFACE=public
OS_APPLICATION_CREDENTIAL_ID=...
OS_APPLICATION_CREDENTIAL_SECRET=...
```

Complete exported `OS_*` application credentials take precedence over `.env`,
and `.env` takes precedence over values in the OpenRC. If the environment is
incomplete, the OpenRC fills missing values. The OpenRC remains the default
fallback.

Use `--model` to override `OPENCODE_MODEL` for a run:

```bash
cve-orchestrator cves.txt --model openai/<model-name>
cve-orchestrator cves.txt --model anthropic/<model-name>
cve-orchestrator cves.txt --model openrouter/deepseek/deepseek-v4-flash-0731
```

Provider and model names must be supported by the installed OpenCode version.
Check a provider directly before a long batch:

```bash
nix develop -c opencode run --format json --model openai/<model-name> "Say ok"
nix develop -c opencode run --format json --model anthropic/<model-name> "Say ok"
```

## 4. DeepSeek V4 Flash 0731 through OpenRouter

OpenCode expects models in `provider/model` form. When an OpenRouter key is
available, the orchestrator accepts the shorter OpenRouter model ID and prefixes
it for OpenCode.

These two model values are equivalent for the orchestrator:

```text
deepseek/deepseek-v4-flash-0731
openrouter/deepseek/deepseek-v4-flash-0731
```

Run:

```bash
cve-orchestrator cves.txt \
  --repo /home/lundi3691/study/phd/nice-archive \
  --workers 2 \
  --timeout-minutes 120 \
  --retries 0 \
  --max-llm-calls 300 \
  --max-input-tokens 4000000 \
  --model deepseek/deepseek-v4-flash-0731 \
  --effort high \
  --resume
```

The command launched for each CVE is shaped like:

```bash
opencode run --format json --auto \
  --model openrouter/deepseek/deepseek-v4-flash-0731 \
  --variant high \
  "..."
```

Use `--agent AGENT_ID` to select another configured OpenCode agent.

The live guard counts each unique `step_finish`/usage generation once as JSONL
arrives. Cache reads are reported separately and do not inflate the input-token
budget. Defaults are 300 LLM calls and 4,000,000 non-cached input tokens per
reproduction attempt; `0` disables either limit. Crossing a limit displays
`BUDGET EXCEEDED`, terminates the OpenCode process group, preserves raw logs and
partial work, and records `status=budget_exceeded`. Final post-exit telemetry is
still parsed independently and remains authoritative.

## 5. Results

Default result artifacts are written under `cves/llm-experiment-results/`.
With the default backend, the host receives the same per-CVE result layout from
the remote VM plus `infrastructure/openstack.json`, `openstack.log`, and
`remote-orchestrator.log`. With `--execution-backend local`, workspaces default
to `/tmp/<repo>-<uid>.cve-copies/CVE-...`; the legacy-named `--worktree-root`
option overrides that root. The source HEAD identified by `--base-ref` is
recorded, while the copy contains the source checkout's current filesystem state.
After the CVE succeeds or the retry policy stops further attempts, the orchestrator copies its
complete matching case directory directly to `CVE-.../recipe/`. It then removes
the local workspace copy when that backend's cleanup policy calls for it.

```text
nice-archive/
└── cves/
    └── llm-experiment-results/
        ├── batch-manifest.json
        ├── batch-summary.json
        ├── summary.csv
        ├── summary.jsonl
        ├── evaluation-batch-manifest.json
        ├── evaluation-batch-summary.json
        ├── CVE-2023-50268/
        │   ├── state.json
        │   ├── readme-handoff.json
        │   ├── readme-handoff.md
        │   ├── infrastructure/
        │   │   ├── openstack.json
        │   │   ├── openstack.log
        │   │   └── remote-orchestrator.log
        │   ├── recipe-manifest.json
        │   ├── recipe/
        │   │   ├── flake.nix
        │   │   ├── flake.lock
        │   │   ├── test.py
        │   │   ├── readme.md
        │   │   ├── EVALUATION.md
        │   │   ├── vm-server.nix
        │   │   └── exploit/...
        │   ├── evaluation/
        │   │   ├── artifact-inventory.json
        │   │   ├── prompt.md
        │   │   ├── command.json
        │   │   ├── opencode-output.jsonl
        │   │   ├── opencode-stderr.log
        │   │   ├── opencode-env.json
        │   │   ├── RECIPE_EVALUATION.json
        │   │   └── result.json
        │   └── llm-logs/
        │       ├── attempt-01/
        │       │   ├── result.json
        │       │   ├── prompt.md
        │       │   ├── command.json
        │       │   ├── EXPERIMENT_RESULT.json
        │       │   ├── opencode-output.jsonl
        │       │   ├── opencode-stderr.log
        │       │   └── opencode-env.json
        │       └── readme-metadata/
        │           ├── input.json
        │           ├── readme-before.md
        │           ├── prompt.md
        │           ├── command.json
        │           ├── opencode-output.jsonl
        │           ├── opencode-stderr.log
        │           ├── opencode-env.json
        │           ├── METADATA_RESULT.json
        │           └── result.json
        ├── human-review-sample.json
        ├── .scenario.lock
        └── ...

/tmp/nice-archive-<uid>.cve-copies/
├── CVE-2023-50268/
├── CVE-2019-10906/
└── ...
```

This is the canonical layout shared by reproduction, inline evaluation,
detached evaluation, summaries, and human sampling. The two
`evaluation-batch-*.json` files exist only after `--evaluate-results`, and
`human-review-sample.json` exists only when sampling is requested. Readers keep
compatibility with older root-level `attempt-XX/` and `worktree-snapshot/`
results, but every new artifact is written only to the canonical layout.
`recipe/EVALUATION.md` is generated after review; it is not a reproduction input.

`summary.csv` is the easiest file to analyze later. A row includes fields such as:

```text
cve,status,execution_backend,openstack_server_id,openstack_destroyed,
openstack_artifacts_synced,attempts,wall_time_seconds,opencode_input_tokens,
opencode_output_tokens,opencode_reasoning_tokens,
opencode_cache_read_tokens,opencode_total_tokens,opencode_tool_calls,
opencode_cost,openrouter_reasoning_tokens,openrouter_cost,
orchestrator_phase,orchestrator_summary,orchestrator_last_error,
evaluation_status,evaluation_verdict,evaluation_summary,
worktree_cleanup_policy,worktree_removed,recipe_path,recipe_manifest,worktree_ref,...
```

Each CVE directory also contains a README handoff pair:

- `readme-handoff.json`: machine-readable state, metadata, orchestrator
  summary, agent result, and artifact paths for a later README-update LLM.
- `readme-handoff.md`: the same information in a compact human-readable form,
  including an instruction to avoid inventing missing metadata.

`llm-logs/attempt-XX/opencode-env.json` records the worker environment summary,
including the scenario lock path used for that attempt.

### Post-reproduction README metadata

After the final reproduction attempt exits, the orchestrator collects OpenCode
usage and runs a separate documentation-only metadata agent. It then copies the
recipe, runs optional evaluation, and applies the repository-copy cleanup policy.
This step also runs when recipe evaluation is disabled.

The reproduction agent leaves final AI metadata pending. The metadata agent
receives measured fields computed from completed attempts using
[`cve-readme-metadata-prompt.md`](./docs/cve-readme-metadata-prompt.md). Python checks
its JSON against those fields and updates only the README's `Reproduction
metadata` section, preserving recorded shell facts and all other sections.
Both the workspace README and its subsequent `recipe/` copy contain the update.

This pass has its own `llm-logs/readme-metadata/` records and original README
backup. Its usage and the evaluator's usage are excluded from reproduction
totals. Model requests are labeled separately from model identities observed
in events. Missing telemetry is not replaced with zero; reported zeroes remain
valid. OpenCode cost is labeled as reported, with no assumed currency or claim
that it equals the provider's invoice. If the agent fails, times out, or changes
values, Python applies the measured fields and records `status=fallback`.
Ambiguous README sections or changes during the pass prevent the update and
are recorded as errors. `state.json`, the JSON handoff, and CSV expose the
metadata-pass status.

Configuration is inherited from the generator, with optional environment
overrides: `CVE_ORCHESTRATOR_METADATA_MODEL`,
`CVE_ORCHESTRATOR_METADATA_AGENT`, `CVE_ORCHESTRATOR_METADATA_EFFORT`, and
`CVE_ORCHESTRATOR_METADATA_TIMEOUT_SECONDS` (1–300; default 300). Provider keys
come from the same process environment. Interrupted reproductions and cases
without a single README are skipped. Detached evaluation and resume-skipped
results do not retroactively edit existing README files.

After all attempts finish, the recipe is copied to `recipe/` regardless of the
repository-copy cleanup policy. The legacy-named `--cleanup-worktrees` option
controls only whether the source copy is then removed; retries never delete or
recreate it:

- `finished` (default): remove completed non-interrupted CVE copies, whether
  successful or failed.
- `success`: cleanup only successful CVEs.
- `always`: cleanup every completed CVE, with the same interruption protection
  as `finished`.
- `never`: keep all per-CVE copies for debugging.

Interrupted copies are retained under every cleanup policy. A later
`--resume` reuses that copy and preserves earlier attempt artifacts.

Cleanup is refused when `--results` and `--worktree-root` are the same
directory, because removing a copy would also risk deleting the result
artifacts. It is also refused when no matching CVE case directory can be
copied. Keep these roots separate for normal batch runs; on any recipe-copy or
cleanup error, the copy remains available for inspection. Cleanup also requires
the adjacent orchestrator marker to match the copy and source repository, so a
legacy Git worktree or unrelated directory is never removed as though it were a
managed copy.

## 6. Success/failure contract

The prompt instructs the agent to create `EXPERIMENT_RESULT.json` near the
beginning with an `inconclusive`/`experiment_incomplete` placeholder, update it
as evidence appears, and overwrite it with the final result before normal
completion:

The built-in prompt also tells the agent to stay in the assigned repository
copy and not create, switch, or require a Git branch or Git worktree.

The orchestrator launches OpenCode with `--dir <workspace-copy>` so tool writes
land in the assigned per-CVE copy, not in the original repository checkout.

```json
{
  "cve": "CVE-2023-50268",
  "status": "success",
  "summary": "...",
  "test_command": "...",
  "test_exit_code": 0,
  "retries": 1,
  "evidence": ["..."],
  "failure_reason": null
}
```

An OpenCode process exiting with code 0 is not automatically treated as a
successful CVE reproduction. The agent must explicitly report `success` in this
file. If the file is absent or malformed, the run is `inconclusive`.
The exact file is also copied to `llm-logs/attempt-XX/EXPERIMENT_RESULT.json`; the parsed
copy embedded in `result.json` is not the only retained representation.

Regardless of status, the orchestrator writes an `orchestrator_summary` into
`llm-logs/attempt-XX/result.json`, the final per-CVE `state.json`, `readme-handoff.json`,
`readme-handoff.md`, and `summary.csv`. This summary is derived from OpenCode
JSONL/stderr logs and Git changes inside the workspace copy. It is meant for triage and README
handoff; it does not replace the case oracle or the agent's
`EXPERIMENT_RESULT.json`.

## 7. Resume

```bash
cve-orchestrator cves.txt \
  --repo /path/to/repo \
  --workers 3 \
  --resume
```

By default, `--resume` uses `--resume-mode success-only`: successful CVEs are
skipped and failed/inconclusive/timeout cases are run again.

For overnight batches where you do not want old failed cases rebuilt:

```bash
cve-orchestrator cves.txt \
  --repo /path/to/repo \
  --workers 3 \
  --resume \
  --resume-mode terminal
```

Resume modes:

- `success-only`: skip only `status=success`.
- `terminal`: skip `success`, `failure`, `inconclusive`, `timeout`,
  `budget_exceeded`, `opencode_error`, `orchestrator_error`, and `interrupted`.
- `existing`: skip any CVE that already has a `state.json`, even if the state
  cannot be parsed.

`--retries` defaults to zero. When nonzero, retries are used only for recognized
transient provider or orchestrator failures (for example rate limiting or a
temporary gateway failure). Success, reproduction failure, inconclusive,
budget-exceeded, interrupted, and timeout attempts are never automatically
retried. OpenStack retries within one CVE invocation stay on that CVE's VM; a
later resumed non-terminal CVE starts in a fresh VM using the host repository
state. The backend best-effort synchronizes partial results before destroying an
interrupted VM. Local retries build on the same copy, and local interruption
retains it. After a local run finishes, the default cleanup policy copies the
complete CVE recipe to `recipe/` and removes the workspace copy. Use
`--cleanup-worktrees never` to retain completed local copies. The option applies
only to the local backend and is retained for CLI and result-schema compatibility.

## 8. Live output

On a normal terminal, running attempts show a compact dashboard such as:

```text
| OpenCode live  active=2/5  workers=2  15:42:10
────────────────────────────────────────────────────────────────
┌─ CVE-2024-23334  attempt 1  03:14  RUNNING ───────────────────
│ Step: Testing vulnerable behavior
│ Tool: pty_spawn
│ Cmd : nix run . -- test --case cve-2024-23334 ...
│
│ Output:
│   machine # booting QEMU...
│   machine # waiting for multi-user.target
│ LLM: 27/300 calls   Input: 1.74M/4.00M   Cached: 320.0k
└───────────────────────────────────────────────────────────────
```

The dashboard is refreshed in place and colored only on TTYs (unless
`NO_COLOR` is set). Non-interactive logs receive concise state changes plus an
occasional compact snapshot. Secrets matching common OpenRouter, GitHub PAT,
and bearer-token forms are redacted in this live view. OpenCode stderr is
forwarded to the orchestrator output as it arrives and remains stored in the
attempt's `opencode-stderr.log`. If a live OpenCode process produces neither
stdout nor stderr for 30 seconds, the orchestrator records and displays a
possible provider-stall warning, repeating it at most once per minute until
output resumes or the configured attempt timeout stops the process.

For OpenStack workers, the host synchronizes attempt artifacts every five
seconds and incrementally feeds new `opencode-output.jsonl` events into the
same dashboard tracker. Current tool names, commands, recent tool output, LLM
calls, and token counters therefore reflect work running inside the experiment
VM rather than only the outer SSH process. Routine OpenCode `INFO` diagnostics
remain in the stderr artifact without replacing tool output in the dashboard.

## 9. OpenRouter metadata caveat

The strongest per-CVE OpenRouter attribution happens when OpenCode output
contains OpenRouter `gen-...` response IDs. The orchestrator queries
`/api/v1/generation` for those IDs and aggregates exact generation statistics.

If no generation IDs are exposed:

- with `--workers 1`, the tool can calculate an OpenRouter API-key spend delta before/after each CVE;
- with multiple workers, a single key's spend delta cannot safely be assigned to an individual CVE, so only the overall batch spend delta is recorded.

## 10. Metadata probe

Run a harmless fake-CVE prompt to verify that OpenCode metadata is visible in
your environment:

```bash
cve-orchestrator \
  --dry-run metadata \
  --execution-backend local \
  --workers 1 \
  --timeout-minutes 5 \
  --retries 0 \
  --results /tmp/otool-probe-results \
  --worktree-root /tmp/otool-probe-copies
```

The probe does not reproduce a vulnerability. It asks the agent only to write
`EXPERIMENT_RESULT.json` and then checks the normal artifact path. Inspect:

```text
/tmp/otool-probe-results/CVE-2099-0001/state.json
/tmp/otool-probe-results/CVE-2099-0001/readme-handoff.json
/tmp/otool-probe-results/CVE-2099-0001/readme-handoff.md
```

## 11. Permissions and isolation

By default, the script passes `--auto` so unattended jobs do not stop at routine
tool approvals. Use `--no-auto` if you prefer stricter OpenCode permission
handling.

The default OpenStack VM is the outer isolation boundary for the coding agent;
vulnerable targets and triggers must still run only in the inner NICE Archive
VMs required by `AGENTS.md`. Avoid placing unrelated credentials in `.env`.
The application credential is used only by the host OpenStack client and is
excluded from repository transfer and Git.

## 12. Stopping a batch

Press Ctrl-C once to request a coordinated shutdown. The orchestrator cancels
CVEs that have not started and sends SIGTERM to active local or SSH process
groups. OpenStack workers attempt a final result sync and VM/keypair deletion,
unless `--openstack-keep-vm` requested intentional retention;
local workers retain interrupted copies. The batch exits with code 130.

Press Ctrl-C a second time to force-kill active OpenCode process groups with
SIGKILL.

## Useful commands

Test one CVE sequentially before launching hundreds:

```bash
head -n 1 cves.txt > one-cve.txt
cve-orchestrator one-cve.txt \
  --repo /path/to/repo \
  --workers 1 \
  --timeout-minutes 120 \
  --retries 0 \
  --model deepseek/deepseek-v4-flash-0731
```

Then scale gradually:

```bash
cve-orchestrator cves.txt \
  --repo /path/to/repo \
  --workers 3 \
  --timeout-minutes 120 \
  --retries 1 \
  --model deepseek/deepseek-v4-flash-0731 \
  --effort high \
  --resume
```

## 13. Independent LLM recipe evaluation

Enable a distinct reviewer process for each reproduction that finishes with
`status=success`:

```bash
cve-orchestrator cves.txt \
  --evaluate-recipes \
  --evaluation-timeout-minutes 90
```

Set generator and reviewer runtime configuration in `.env` or the process
environment. `OPENCODE_MODEL`, `OPENCODE_AGENT`, and `OPENCODE_VARIANT` select
the generator. `CVE_ORCHESTRATOR_EVALUATION_MODEL`,
`CVE_ORCHESTRATOR_EVALUATION_AGENT`, and
`CVE_ORCHESTRATOR_EVALUATION_EFFORT` optionally override those values for the
reviewer; without overrides, the reviewer inherits the generator settings. The
provider is the prefix in the model value, and standard provider credentials
such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `OPENROUTER_API_KEY` are
inherited from the same environment. Credentials are never placed in the
evaluator prompt, command JSON, or environment summary.

The default evaluator prompt is
[`cve-recipe-evaluator-prompt.md`](./docs/cve-recipe-evaluator-prompt.md). Use
`--evaluation-prompt-file` to replace it. A custom prompt can use `{cve}`,
`{recipe_path}`, `{recipe_inventory}` (embedded JSON), and `{result_path}`.
The legacy `{artifact_root}` marker now aliases the recipe root. Legacy
`{state_path}`, `{inventory_path}`, and `{worktree_path}` markers yield
scope/unavailability notices, not external input paths. Every custom prompt
is prefixed with the same recipe-only scope instruction.

Before review, the orchestrator copies the matching case into `recipe/` and
writes `evaluation/artifact-inventory.json`. The evaluator inspects that frozen
recipe only, with its working directory set to the recipe root. The inventory
is embedded in the prompt so the reviewer need not open external files. It
reads CVE descriptions, advisory/fix excerpts, and PoC material bundled within
the recipe as text, then compares
the documented scope with configuration, installation/version evidence,
source pins, reproducibility, file layout, and test structure. It records read
and unverified references separately. External URLs and paths are citations;
the reviewer does not fetch them, follow outside symlinks, or inspect other
workspace copies or parent directories.

Evaluation is a documentation and evidence review. It does not run scenarios,
tests, builds, services, or PoCs. Automated vulnerable/fixed outcomes are graded
from evidence included in the recipe, such as bundled logs or specific README
output excerpts. A bare "tests passed" claim is insufficient; missing evidence
is `unverified`, without searching external attempt logs.
Manual observations are not required evaluation checks, although documented
unsafe historical execution and false statements remain reportable findings.
Pending telemetry from before OpenCode exited is not a documentation failure
merely because the orchestrator obtained final figures afterward.

Rubric version 3 restricts required artifacts to recipe contents: `flake.nix`,
`flake.lock`, `test.py`, README, VM/module configuration, and trigger artifacts.
Orchestrator state, manifests, handoffs, attempt logs, and raw
`EXPERIMENT_RESULT.json` are not requirements and their absence cannot fail a
recipe. Legacy snapshot case directories are equally valid recipe roots.
The orchestrator still uses result state for batch selection and eligibility;
it does not supply that state as evidence to the reviewer.

The reviewer may write only `evaluation/RECIPE_EVALUATION.json`; this outside
path is write-only output. The orchestrator hashes
the recipe inputs before and after review and invalidates the review
if they change. Its machine validator requires all eleven named requirement checks,
valid statuses, evidence for every passing check, list-valued missing-artifact,
concern, and command fields, and consistent overall verdict logic. It also
forces a failed evaluation when the deterministic preflight inventory is
incomplete. Thus an evaluator's prose or self-declared `pass` cannot bypass the
artifact contract.

After validation, the orchestrator renders `recipe/EVALUATION.md` from the
JSON, including final status, reviewer summary, a checklist with evidence
excerpts, missing recipe files, concerns, validation findings, reference notes,
and review metadata. It shows the validator's final status even when that
differs from the LLM verdict. The full JSON remains linked for detail.
This report is written after input-change checks, excluded from subsequent
inventories, and explicitly ignored by later reviews. Reevaluation replaces
the generated report. A non-generated file with the same name is preserved
and recorded as `report_error`. For legacy results the report is written into
the resolved legacy recipe directory. The path is saved in the evaluation's
`artifacts.report` field, and consequently in `state.json` and its handoff.

Evaluation is additive: it never changes the reproduction `status`. The
details are stored in `state.json`, `readme-handoff.*`, `summary.csv`, and the
`evaluation/` directory. Resume preserves an existing evaluation; pass
`--reevaluate` together with `--evaluate-recipes` to replace it. When every
reproduction succeeded but an enabled evaluation failed or was inconclusive,
the orchestrator exits with status 3 (reproduction failures retain status 2).

### Detached evaluation after reproduction

Use `--evaluate-results` to run evaluation later as a separate batch step. This
mode reads completed `state.json` files and retained `recipe/` directories from
`--results`; it does not create workspace copies or start any reproduction attempt:

```bash
cve-orchestrator \
  --evaluate-results \
  --results cves/llm-experiment-results \
  --workers 2
```

With no CVE list, every `CVE-*/state.json` under the results directory is
considered. Only successful reproductions are eligible; failed and
inconclusive reproductions receive a skipped evaluation. Provide a CVE list to
scope the detached step:

```bash
cve-orchestrator selected-cves.txt \
  --evaluate-results \
  --results cves/llm-experiment-results
```

Existing evaluations are preserved. Add `--reevaluate` to replace them. The
detached step updates each selected `state.json`, its README handoff, and
`summary.csv`, while leaving the original `batch-manifest.json` and
`batch-summary.json` untouched. Its own run metadata is written to
`evaluation-batch-manifest.json` and `evaluation-batch-summary.json`.

Detached and inline evaluations use the same recipe-only documentation/evidence rubric,
including when a worktree was retained. Existing evaluations keep their prior
rubric and verdict until explicitly replaced with `--reevaluate`.

## 14. Random human-review sample

Print a random subset of successful, artifact-backed recipes after the batch:

```bash
cve-orchestrator cves.txt \
  --resume \
  --human-review-sample 10
```

The stdout block gives each selected CVE, retained recipe path, `state.json`, and
evaluation status. The full selection is retained in
`human-review-sample.json`.

Sampling uses only successful recipes whose retained recipe directory can be
resolved. If the requested count exceeds that population, all eligible recipes
are selected and stdout reports the reduced count.
