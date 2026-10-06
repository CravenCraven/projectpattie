---
num: "06"
title: "Livros"
sub: "Audiobookshelf"
blurb: "Podcasts and audiobooks"
section: "midia"
status: "planned"
color: "c5"
order: 6
---

## What it is

Audiobookshelf for Portuguese podcasts and audiobooks, with listening progress tracked.

## The plan

Same pattern as Música: a Flux-managed Deployment, media on a local-path volume, loaded by rsync. local-path volumes cannot be expanded after creation, so the size is set once and has to be right the first time.

## Status

Planned. Runbook written, not deployed.
