---
num: "05"
title: "Música"
sub: "Navidrome"
blurb: "Samba, MPB, choro"
section: "midia"
status: "running"
color: "c3"
order: 5
---

## What it is

Navidrome is a self-hosted music server. Think Spotify, except the library is mine and it runs on my own cluster.

Music is the easiest way into Portuguese. You hear the rhythm and the slang long before you can read it, and a song you like gets played fifty times.

## What's in it

Samba, MPB and choro. A handful of albums to start.

## How it runs

Navidrome runs on the k3s cluster, deployed through Flux like everything else. The music sits on a local volume, which means it lives in a folder on one node. Adding albums is an rsync from my Mac to that machine.

The one surprise was a config setting that did nothing. The container ignored an environment variable it didn't recognise, and Flux still reported success. The application logs were where the gap showed.

## Status

Running privately. It goes public later through a Cloudflare Tunnel, behind a login.
