# CVE OpenCode batch orchestrator

`cve-orchestrator` runs one OpenCode agent job per CVE, using an isolated Git
worktree for each CVE. It supports parallel workers, retries, hard attempt
timeouts, resume, live interaction output, and optional OpenRouter metadata
enrichment.

## What it records

For every attempt it records:

- wall-clock execution time
- OpenCode exit code / timeout state
- agent-declared reproduction result (`success`, `failure`, or `inconclusive`)
- best-effort OpenCode token, cost, model, LLM-call, and tool-call metadata from JSON events
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
opencode_output_tokens,opencode_total_tokens,opencode_tool_calls,
opencode_cost,openrouter_reasoning_tokens,openrouter_cost,...
```

## 5. Success/failure contract

The prompt instructs the agent to create `EXPERIMENT_RESULT.json` in its
worktree root before it finishes:

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

## 6. Resume

```bash
cve-orchestrator cves.txt \
  --repo /path/to/repo \
  --workers 3 \
  --resume
```

Successful CVEs are skipped. Failed/inconclusive CVEs are run again. Worktrees
are deliberately kept so you can inspect failed runs and so a retry can build on
the previous attempt.

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

## 9. Permissions and isolation

By default, the script passes `--auto` so unattended jobs do not stop at routine
tool approvals. Use `--no-auto` if you prefer stricter OpenCode permission
handling.

For CVE/PoC experiments, run the batch on an isolated research machine/VM and
avoid placing unrelated credentials in the agent environment.

## 10. Stopping a batch

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
