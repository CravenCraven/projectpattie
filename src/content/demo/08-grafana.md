---
num: "08"
title: "Grafana"
sub: "kube-prometheus-stack"
blurb: "Node and pod metrics, k3s-adjusted scrape config"
section: "infra"
status: "planned"
color: "c4"
order: 8
---

## What it is

Prometheus, Grafana and node-exporter for node and pod metrics across the cluster.

## The plan

kube-prometheus-stack, pinned to the heavy worker.

- Four default scrape targets disabled, because k3s bundles those components into a single binary and the endpoints do not exist
- Alertmanager disabled on purpose. There is no one to page
- Dashboards: Node Exporter Full (1860) and Kubernetes Views Pods (15760)
- The Grafana admin secret is imperative for now and moves to a SealedSecret later

## Status

Planned. Manifests are generated. Waiting on a disk and memory preflight on the worker, since Prometheus retention has to fit a fixed-size local-path volume.
