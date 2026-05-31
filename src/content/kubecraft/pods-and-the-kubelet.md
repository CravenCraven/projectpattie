---
title: "Pods, the Kubelet, and Why My Container Kept Restarting"
date: 2026-05-31
section: "core concepts"
confidence: 3
timeSpent: "50 min"
tags: ["pods", "kubelet", "kubectl", "debugging"]
difficulty: "medium"
energy: "coffee++"
nextGoal: "Services & networking — ClusterIP vs NodePort"
draft: false
---

## What I Learned

A Pod is the smallest deployable unit in Kubernetes, but the mental model that finally stuck is that a Pod is a *wrapper around one or more containers that share a network namespace and storage*. They get one IP between them and can talk to each other over `localhost`.

The kubelet is the agent running on every node. It doesn't create Pods out of thin air — it watches the API server for Pods assigned to its node, then makes the container runtime actually run them. If a container dies, the kubelet is the thing that notices and restarts it according to the `restartPolicy`.

- A Pod is not a container — it's a group of containers plus shared context
- The kubelet reconciles desired state (from the API server) against actual state on the node
- `restartPolicy` lives on the Pod, not the container

## My Thoughts

This clicked once I stopped thinking of Pods as "a fancy word for container." The shared network namespace is the whole point — it's why a sidecar pattern works at all.

**Connections:** this is a lot like systemd on a single host — the kubelet plays the role systemd does, watching a desired unit state and restarting things that fall over. Except the "desired state" comes from a central API server instead of unit files on disk.

> The kubelet is pull-based, not push-based. The scheduler assigns a Pod to a node, but nothing *pushes* it there — the kubelet pulls its assigned work from the API server. Internalizing that explained half my confusion about how Pods "get" to a node.

## Code Snippets

### see which node a pod landed on and why it's unhappy

```kubectl
kubectl get pods -o wide
kubectl describe pod web-7d9f -n demo
```

### a minimal pod spec with an explicit restart policy

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web
  namespace: demo
spec:
  restartPolicy: Always
  containers:
    - name: web
      image: nginx:1.27
      ports:
        - containerPort: 80
```

### watch the kubelet's view of restarts climb

```bash
kubectl get pod web -n demo -w
```

## Mistakes & Fixes

**What broke:** My container went into `CrashLoopBackOff` and I assumed the image was bad. It wasn't — the process was exiting cleanly with code 0, and `restartPolicy: Always` kept bringing it back, which *looked* like a crash loop.

**How I fixed it:** Switched the workload to a long-running process (the container was running a one-shot script that finished immediately). For genuinely one-shot work, a Job with `restartPolicy: OnFailure` is the right tool, not a bare Pod.

```bash
Back-off restarting failed container web in pod web_demo
Last state: Terminated  Reason: Completed  Exit Code: 0
```

The `Exit Code: 0` was the tell — a healthy exit, not a failure.

## Aha Moment

`CrashLoopBackOff` doesn't mean "your app crashed." It means "the container keeps stopping and the kubelet keeps restarting it, and the gaps between restarts are growing." The *why* is in `Last state` / `Exit Code` — and exit code 0 means nothing is actually wrong except my expectations.

## Questions to Research

- What's the actual back-off curve? Is it exponential, and is there a cap?
- Difference between `restartPolicy` on a Pod vs the restart behavior a Deployment gives you
- How does a readiness probe interact with all this — does a failing probe count as a restart?

## Real World Application

In the home lab this is exactly the bug I'll hit running batch/cron-style work. Now I know to reach for a Job or CronJob instead of forcing a Pod to stay alive, and to read `Exit Code` before blaming the image. At work this is the same reasoning behind "is this service crashing, or is it just doing its job and exiting?"
