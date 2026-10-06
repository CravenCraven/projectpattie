---
num: "04"
title: "Gíria"
sub: "CloudNativePG"
blurb: "Carioca slang database, fed by coach output"
section: "aprender"
status: "planned"
color: "c4"
order: 4
---

## What it is

A database of Carioca slang, built from the errors the Coach catches in my own writing.

## The plan

Postgres on CloudNativePG. One instance, no replicas. local-path storage pins a volume to one node, so a replica scheduled anywhere else could not reach its data.

## Status

Deferred to v2.
