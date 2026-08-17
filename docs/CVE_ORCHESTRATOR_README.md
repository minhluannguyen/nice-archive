# CVE OpenCode batch orchestrator

`cve-orchestrator` runs one OpenCode agent job per CVE, using an isolated
detached Git worktree directory for each CVE. It supports parallel workers,
retries, hard attempt timeouts, resume, live interaction output, and optional
OpenRouter metadata enrichment.

## What it records

For every attempt it records:

- wall-clock execution time
- OpenCode exit code / timeout state
- agent-declared reproduction result (`success`, `failure`, or `inconclusive`)
- orchestrator-generated fallback summary from logs and worktree state, even
  when the agent omits or corrupts `EXPERIMENT_RESULT.json`
- best-effort OpenCode input, output, reasoning, cache, total token, cost,
  model, LLM-call, and tool-call metadata from JSON events
- full OpenCode JSONL output and stderr
- OpenRouter prompt/completion/reasoning/cached token counts, provider, model, latency, and cost when an OpenRouter generation ID is available

The runner does not ask the LLM to estimate its own token use. Per-CVE
OpenRouter attribution is exact when OpenRouter `gen-...` IDs appear in
OpenCode output. Otherwise, sequential runs can still record an API-key spend
delta.

While jobs are running, the orchestrator shows a live dashboard with one column
per visible worker: CVE, attempt, elapsed time, status, and recent sanitized
OpenCode stdout/stderr snippets. The full raw streams are still written to the
attempt artifacts. Use `--live` to force this display when stderr is not a TTY,
or `--no-live` for quiet batch logs.

## 1. Prepare the CVE list

```text
CVE-2023-50268
CVE-2019-10906
CVE-2021-23980
CVE-2024-23334
```

Blank lines and `#` comments are ignored.

## 2. OpenCode setup

Inside `nix develop`, use the packaged binary directly. Outside the dev shell,
prefix commands with `nix run .#cve-orchestrator --`.

The flake includes Nixpkgs' `opencode` package, which provides the `opencode`
binary used by default.

Set the OpenRouter key in the shell or repository `.env`:

```bash
export OPENROUTER_API_KEY='sk-or-v1-...'
```

OpenCode also reads `.env` itself. The orchestrator loads simple `KEY=VALUE`
entries from the repository `.env` for its own metadata and key checks.

## 3. DeepSeek V4 Flash 0731 through OpenRouter

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
  --timeout-minutes 45 \
  --retries 1 \
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

Use `--agent AGENT_ID` if you have an OpenCode agent configured for this
workflow.

## 4. Results

Default result artifacts are written under `cves/llm-experiment-results/`.
Per-CVE worktrees are detached at `--base-ref`, so the orchestrator does not
create experiment branches.

```text
nice-archive/
└── cves/
    └── llm-experiment-results/
        ├── batch-manifest.json
        ├── batch-summary.json
        ├── summary.csv
        ├── summary.jsonl
        ├── CVE-2023-50268/
        │   ├── state.json
        │   ├── readme-handoff.json
        │   ├── readme-handoff.md
        │   └── attempt-01/
        │       ├── result.json
        │       ├── opencode-output.jsonl
        │       ├── opencode-stderr.log
        │       └── opencode-env.json
        └── ...

../nice-archive.cve-worktrees/
├── CVE-2023-50268/
├── CVE-2019-10906/
└── ...
```

`summary.csv` is the easiest file to analyze later. A row includes fields such as:

```text
cve,status,attempts,wall_time_seconds,opencode_input_tokens,
opencode_output_tokens,opencode_reasoning_tokens,
opencode_cache_read_tokens,opencode_total_tokens,opencode_tool_calls,
opencode_cost,openrouter_reasoning_tokens,openrouter_cost,
orchestrator_phase,orchestrator_summary,orchestrator_last_error,worktree_ref,...
```

Each CVE directory also contains a README handoff pair:

- `readme-handoff.json`: machine-readable state, metadata, orchestrator
  summary, agent result, and artifact paths for a later README-update LLM.
- `readme-handoff.md`: the same information in a compact human-readable form,
  including an instruction to avoid inventing missing metadata.

## 5. Success/failure contract

The prompt instructs the agent to create `EXPERIMENT_RESULT.json` in its
worktree root before it finishes:

The built-in prompt also tells the agent to stay in the assigned detached
worktree directory and not create, switch, or require a separate Git branch for
the experiment.

The orchestrator launches OpenCode with `--dir <worktree>` so tool writes land
in the assigned per-CVE worktree, not in the original repository checkout.

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

Regardless of status, the orchestrator writes an `orchestrator_summary` into
`attempt-XX/result.json`, the final per-CVE `state.json`, `readme-handoff.json`,
`readme-handoff.md`, and `summary.csv`. This summary is derived from OpenCode
JSONL/stderr logs and Git worktree changes. It is meant for triage and README
handoff; it does not replace the case oracle or the agent's
`EXPERIMENT_RESULT.json`.

## 6. Resume

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
  `opencode_error`, `orchestrator_error`, and `interrupted`.
- `existing`: skip any CVE that already has a `state.json`, even if the state
  cannot be parsed.

Worktrees are deliberately kept so you can inspect failed runs and so a retry
can build on the previous attempt when the resume policy allows it.

## 7. Live output

On a normal terminal, running attempts show a compact dashboard such as:

```text
/ OpenCode live  active=2/5  workers=2  15:42:10
---------------------------------------------------
CVE-2024-23334  a1  03:14        CVE-2019-6111  a1  02:58
status: running                   status: running
stdout: session.updated           stdout: tool.call | tool=bash
stderr: running nix eval          stdout: message.completed | tokens=1200/340
```

The dashboard is refreshed in place on TTYs and printed periodically in
non-interactive logs. Secrets matching common OpenRouter, GitHub PAT, and
bearer-token forms are redacted in this live view.

## 8. OpenRouter metadata caveat

The strongest per-CVE OpenRouter attribution happens when OpenCode output
contains OpenRouter `gen-...` response IDs. The orchestrator queries
`/api/v1/generation` for those IDs and aggregates exact generation statistics.

If no generation IDs are exposed:

- with `--workers 1`, the tool can calculate an OpenRouter API-key spend delta before/after each CVE;
- with multiple workers, a single key's spend delta cannot safely be assigned to an individual CVE, so only the overall batch spend delta is recorded.

## 9. Metadata probe

Run a harmless fake-CVE prompt to verify that OpenCode metadata is visible in
your environment:

```bash
cve-orchestrator \
  --metadata-probe \
  --workers 1 \
  --timeout-minutes 5 \
  --retries 0 \
  --results /tmp/otool-probe-results \
  --worktree-root /tmp/otool-probe-worktrees
```

The probe does not reproduce a vulnerability. It asks the agent only to write
`EXPERIMENT_RESULT.json` and then checks the normal artifact path. Inspect:

```text
/tmp/otool-probe-results/CVE-2099-0001/state.json
/tmp/otool-probe-results/CVE-2099-0001/readme-handoff.json
/tmp/otool-probe-results/CVE-2099-0001/readme-handoff.md
```

## 10. Permissions and isolation

By default, the script passes `--auto` so unattended jobs do not stop at routine
tool approvals. Use `--no-auto` if you prefer stricter OpenCode permission
handling.

For CVE/PoC experiments, run the batch on an isolated research machine/VM and
avoid placing unrelated credentials in the agent environment.

## 11. Stopping a batch

Press Ctrl-C once to request a coordinated shutdown. The orchestrator cancels
CVEs that have not started, sends SIGTERM to every active OpenCode process
group, writes interrupted state/result metadata where possible, and exits with
code 130.

Press Ctrl-C a second time to force-kill active OpenCode process groups with
SIGKILL.

## Useful commands

Test one CVE sequentially before launching hundreds:

```bash
head -n 1 cves.txt > one-cve.txt
cve-orchestrator one-cve.txt \
  --repo /path/to/repo \
  --workers 1 \
  --timeout-minutes 30 \
  --retries 0 \
  --model deepseek/deepseek-v4-flash-0731
```

Then scale gradually:

```bash
cve-orchestrator cves.txt \
  --repo /path/to/repo \
  --workers 3 \
  --timeout-minutes 45 \
  --retries 1 \
  --model deepseek/deepseek-v4-flash-0731 \
  --effort high \
  --resume
```
