---
num: "01"
title: "Tutor"
sub: "Open WebUI + Ollama"
blurb: "Conversation practice against a local 7B model"
section: "aprender"
status: "running"
color: "c1"
order: 1
---

## What it is

A Portuguese conversation partner. Open WebUI is the front end. Inference runs in-cluster on Ollama, so no prompt ever leaves the network.

## What's in it

qwen2.5 7B as the single model. It holds a conversation in Portuguese. Carioca slang is where it drifts, which is what the Gíria tile is eventually for.

## How it runs

A Deployment in the `brasil` namespace, reconciled by Flux from a flat `clusters/staging/brasil/` layout. User accounts live in a SQLite database on the pod's volume at `/app/backend/data/webui.db`.

Access today is `kubectl port-forward svc/open-webui 8080:80`. Port-forward binds to localhost on the machine that runs it, so it has to run where the browser is. Running it inside an SSH session to the server gave me a connection reset on my Mac.

The first login failed on the password. The image ships Python but not the sqlite3 binary, so I queried the database read-only through Python, backed it up, and wrote a new bcrypt hash to exactly one row.

## Status

Running, private. Next is a Cloudflare Tunnel with Cloudflare Access in front, after Música.
