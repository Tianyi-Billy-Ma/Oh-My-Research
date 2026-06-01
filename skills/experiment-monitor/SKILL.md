---
id: experiment-monitor
name: experiment-monitor
version: 0.17.0
argument-hint: [job-handle-or-log-path]
description: |-
  Watch a running experiment on an adaptive cadence — frequent checks during the failure-prone startup, sparse checks once training is stable.
stages: ["experiment"]
tools: ["Bash", "Read", "Grep", "Glob", "AskUserQuestion"]
summary: |-
  A monitoring policy for long-running experiments. It does NOT prescribe how to observe the job (the agent picks: log tail, ssh to the HPC host, squeue/sacct, a status file) or how to detect the training transition (the agent reads the logs and judges startup vs stable training). It DOES provide the waiting policy: a tight interval while the job is in the failure-prone startup window, a sparse interval once training is underway, both read from config.yaml's monitor block, with checks handed off to scheduled wake-ups so the session isn't blocked.
primaryIntent: experiment
intents: ["experiment", "tooling"]
capabilities: ["infrastructure-ops"]
domains: ["general"]
keywords: ["omr-experiment-monitor", "omr:experiment-monitor", "monitor experiment", "monitor my job", "watch my job", "watch the training run", "check on training", "is my job still running", "babysit experiment", "monitor training", "keep an eye on the experiment", "poll the job"]
source: builtin
status: experimental
resourceFlags:
  hasReferences: false
  hasScripts: false
  hasTemplates: false
  hasAssets: false
  referenceCount: 0
  scriptCount: 0
  templateCount: 0
  assetCount: 0
---

# omr:experiment-monitor

Watch a running experiment without babysitting it by hand. The insight this
skill encodes: **failures cluster at startup** — environment/dependency
loading, dataset and collator construction, config parsing, model/checkpoint
loading, kernel compilation — and once a run reaches *stable training* (loss
values printing, steps/epochs advancing), it rarely errors mid-flight. So
check **tight** during startup and **back off** once training is stable.

**When this skill is invoked, immediately execute the workflow below. Do
not just restate or summarize these instructions back to the user.**

This skill gives you a **waiting policy**, not a fixed recipe. It does not
tell you exactly *how* to look at the job or exactly *when* training began —
you decide those from what you actually observe. It tells you *how often* to
look and *when to back off*.

## Best-fit use

Choose this skill when an experiment/training job is **already running** (or
just submitted) and the user wants it watched until it finishes or fails,
without sitting and polling manually. Pair it with a future `/omr:experiment`
(which submits jobs) — but it stands alone: point it at any running job.

Do **not** use it to submit or launch a job, to analyze results after a run
completes, or to manage the job queue — those are separate concerns.

## What this skill does NOT prescribe (use your judgment)

1. **How to observe the job.** Use whatever signal is most direct for *this*
   job — tail a local log file; `ssh <host> "tail -n 50 <log>"` with the host
   and paths resolved from `./.omr/hpc/<cluster>.yaml`; query the scheduler
   (`squeue`/`sacct` for SLURM, `qstat` for PBS); read a status/heartbeat
   file the run writes; or a combination. The skill deliberately does not
   limit the method.
2. **How to detect the startup→training transition.** Read the logs/status
   and *reason* about which phase the job is in — do not rely on a single
   hardcoded marker. Signs of stable training: loss/metric values printing on
   a regular cadence, step or epoch counters advancing, steady
   throughput/iteration time, GPU utilization holding. Signs of still-in-
   startup: import/CUDA messages, "building dataset", "loading checkpoint",
   compilation, or simply no training-step output yet.

## The waiting policy (the point of this skill)

Read the two intervals from `./.omr/config.yaml` `monitor:` block:

- `early_interval_minutes` (default `1`) — cadence while the job is in the
  failure-prone startup window.
- `training_interval_minutes` (default `15`) — cadence once you judge the job
  to be in stable training.

If `config.yaml` has no `monitor:` block, use the defaults (1 / 15) and
mention it once.

Cadence rule:

- **Startup phase** → re-check every `early_interval_minutes`. Failures are
  most likely here, so catch them fast and surface them immediately.
- **Stable-training phase** → re-check every `training_interval_minutes`.
  The run is unlikely to error now; checking more often just wastes effort.
- Re-evaluate the phase on **every** check — if a job that looked like it was
  training falls back to setup output (e.g. a restart), drop back to the
  early interval.

## Hand off to scheduled wake-ups (don't block the session)

Training can run for hours. Do **not** sit in a long in-session `sleep`. After
each check, **schedule the next check** at the current phase's interval using
the recurring wake-up mechanism (e.g. the `loop` capability / a scheduled
wake-up), so the session is free between checks. On each wake:

1. Observe the job (your chosen method).
2. Classify the state: `starting` / `training` / `completed` / `failed` /
   `stalled` (log stopped growing / heartbeat gone).
3. Report a one-line status to the user.
4. Decide the next step:
   - `starting` → reschedule at `early_interval_minutes`.
   - `training` → reschedule at `training_interval_minutes`.
   - `completed` → stop; report success and where the outputs/checkpoints are.
   - `failed` → **stop and surface the error now** (tail the relevant log
     lines). This is the payoff of the tight early cadence.
   - `stalled` → don't guess; ask the user via `AskUserQuestion`
     ("No log growth for <N>; keep waiting / stop monitoring / investigate?").

Pick the wake-up interval from the phase you just observed, not the one you
assumed at the previous check.

## Safety rails

1. **Read-only.** Observe the job; never modify, kill, pause, or resubmit it.
   If the user wants to act on a failure, that's their call — surface the
   evidence and let them decide.
2. **Never fabricate status.** Report only what the logs / scheduler actually
   show. If you can't reach the job (ssh failed, log missing), say so and ask
   how to proceed — don't invent "still running."
3. **Surface failures immediately**, especially during startup. Don't wait
   for the next scheduled check if a check already shows a crash.
4. **Every decision point goes through `AskUserQuestion`** (stalled job, lost
   connection, ambiguous state) — never a free-text prompt.
5. **No secrets in output.** If observing requires a credential pointer
   (e.g. an ssh key path from the HPC config), use it; never print its value.

## Out of scope

- Submitting/launching experiments (future `/omr:experiment`).
- Analyzing or plotting results after completion.
- Killing, resubmitting, or otherwise managing jobs.
