---
num: "09"
title: "Ollama"
sub: "qwen2.5 7b q4_K_M"
blurb: "CPU inference, 20Gi limit, measured 4.6 tok/s"
section: "infra"
status: "running"
color: "c1"
order: 9
---

## What it is

The inference backend behind the Tutor. Internal only. Nothing talks to it except Open WebUI.

## What's in it

qwen2.5 7B at q4_K_M quantization, sized to run on CPU with no GPU in the cluster.

## How it runs

Scheduled with a nodeSelector on `workload=heavy`, the amd64 Fedora worker with the most memory. Labels describe capability, not hardware, so the workload follows the label if the node changes.

- 20Gi memory limit
- `KEEP_ALIVE=30m` so the model stays loaded between sessions instead of cold-loading every prompt
- Pinned image tag, no `latest`
- `strategy: Recreate`, because a single local-path volume cannot be mounted by two pods during a rolling update
- Startup probe, so a slow model load is not mistaken for a crash

Measured throughput is about 4.6 tokens per second. Modelfile and prompt changes ship as a ConfigMap with a hash suffix, so a change produces a new name and forces a rollout.

## Status

Running.
