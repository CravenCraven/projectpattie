---
num: "03"
title: "Fichas"
sub: "Anki export"
blurb: "Decks generated from the corpus, with audio"
section: "aprender"
status: "planned"
color: "c3"
order: 3
---

## What it is

Anki decks generated from the course corpus, with the original audio attached to each card.

## The plan

Reads from the Postgres corpus that fsi-scraper loads. Sources are the FSI Brazilian Portuguese courses and COERLL from UT Austin. The deck generator never touches raw course files. It only reads the database.

## Status

Planned. Waits on fsi-scraper reaching the load stage.
