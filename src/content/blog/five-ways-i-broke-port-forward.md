---
title: "Five ways I broke port-forward in one night"
description: "One command, two numbers, and every one of them wrong at some point while I tested Navidrome and Open WebUI."
date: 2026-09-24
category: devops
readTime: 7
homelab: brasil
draft: false
---

## How this started

Thursday night I tested two tiles in the Brasil homelab: Música, which is Navidrome, and the Tutor, which is Open WebUI in front of Ollama. Neither one is on the internet yet, so the way I reach them is `kubectl port-forward`.

It is one line with two numbers in it. I got it wrong five different ways before the night was over.

Every error told me what was wrong. I just had to read it instead of retyping the command.

## The checklist had the wrong port

My checklist said to test Navidrome with this:

```bash
kubectl -n brasil port-forward svc/navidrome 4533:4533
```

I caught this one before running it, because I had just looked at the service:

```bash
kubectl -n brasil get svc | grep navidrome
#    -> service/navidrome   ClusterIP   ...   80/TCP   37d
```

The format is `LOCAL:REMOTE`. When you forward to a service, the remote number has to be a port the service exposes. Navidrome listens on 4533 inside the pod, but the service in front of it is on 80. I had written the pod's port where the service's port goes.

```bash
kubectl -n brasil port-forward svc/navidrome 4533:80
#    -> Forwarding from 127.0.0.1:4533 -> 4533
```

The output says `-> 4533` even though I typed 80. kubectl looked up the service, saw that 80 points to 4533, and went straight to the pod.

## The forward died when the pod did

This one got me twice.

The first time, I pushed a fix to the Navidrome manifest and Flux rolled out a new pod. My port-forward in the other tab stopped working. I did not think much of it.

The second time, I did it on purpose. I restarted Navidrome to prove my library would survive:

```bash
kubectl -n brasil rollout restart deploy/navidrome
kubectl -n brasil get pods | grep navidrome
#    -> navidrome-7c4d684dd9-5jfnv   1/1   Running   0   10s
```

I refreshed the browser:

```
localhost refused to connect.
ERR_CONNECTION_REFUSED
```

For a second I thought the library was gone. It was not. Port-forward picks one pod when it starts and stays attached to that pod. Even if you point it at a service, it is not load balancing. The old pod was deleted, the forward went with it, and nothing was listening on 4533 on my Mac anymore.

Refused means there is nothing on the other end. I stopped the forward, started it again, and it attached to the new pod.

**worth knowing:** this is why port-forward is for testing. A real service or ingress follows the pods through restarts. Port-forward does not.

## A terminal full of broken pipes

With the forward running and Navidrome open, the terminal filled up with this:

```
E0924 20:40:10.820561   87651 portforward.go:489] "Unhandled Error" err="error copying from remote stream to local connection: readfrom tcp6 [::1]:4533->[::1]:59846: write tcp6 [::1]:4533->[::1]:59846: write: broken pipe"
E0924 20:41:32.837013   87651 portforward.go:489] "Unhandled Error" err="... write: connection reset by peer"
```

"Unhandled Error" in red, over and over. Meanwhile, in the browser, my albums were loading and the music was playing.

These come from the browser closing a connection before the forward is done sending. Click to another page, and the browser drops the requests it no longer needs. Port-forward logs every one of them like something broke.

If the app is working, this is noise. I only worry about it if the page stops loading.

## Three tries at a service name

Next was the Tutor. My first draft of the command was:

```bash
kubectl -n brasil port-forwarding svc/ollama
```

Three things wrong with that. The verb is `port-forward`, not `port-forwarding`, which I had actually typed. There are no ports. And Ollama is the wrong service. It is the model backend, an API with no web page. The thing I open in a browser is Open WebUI.

So I checked the service list:

```bash
kubectl -n brasil get pods,svc | grep -i -e ollama -e webui
#    -> service/ollama       ClusterIP   ...   11434/TCP   38d
#    -> service/open-webui   ClusterIP   ...   80/TCP      38d
```

Port 80, same as Navidrome. I had the ports right on the first try. The name took three.

```bash
kubectl -n brasil port-forward svc/service/open-webui 8080:80
#    -> error: arguments in resource/name form may not have more than one slash
```

The output shows `service/open-webui`. I copied that and put `svc/` in front of it. But `service/open-webui` is already a type and a name. `svc` and `service` are the same type, so I had written it twice.

```bash
kubectl -n brasil port-forward svc/service-open-webui 8080:80
#    -> Error from server (NotFound): services "service-open-webui" not found

kubectl -n brasil port-forward svc/open-webui-service 8080:80
#    -> Error from server (NotFound): services "open-webui-service" not found
```

These two are a different kind of error. `Error from server` means kubectl understood the command fine and sent it to the cluster. The cluster just did not have a service by that name. At this point I was guessing.

The name is whatever comes after the slash. Nothing added.

```bash
kubectl -n brasil port-forward svc/open-webui 8080:80
#    -> Forwarding from 127.0.0.1:8080 -> 8080
```

## Right command, wrong machine

The forward was running. I opened `localhost:8080` on my Mac.

```
This site can't be reached
The connection was reset.
ERR_CONNECTION_RESET
```

Then I looked at the prompt on the terminal where the forward was running.

```
op@server:~$ kubectl -n brasil port-forward svc/open-webui 8080:80
```

I was on the control plane. I had run every Tutor command on the server over SSH, and then I kept going and ran the forward there too.

Port-forward listens on `127.0.0.1`, which means this machine only. The forward was waiting on the server's localhost. My browser was asking my Mac's localhost. Those are two different machines.

I wrote [a whole post four days ago](/blog/my-daily-driver-was-talking-to-the-wrong-cluster/) about checking where I am before blaming the cluster. And here I was.

I stopped it on the server and ran the same command on my daily driver:

```
op@mac:~$ kubectl -n brasil port-forward svc/open-webui 8080:80
```

The Open WebUI login page came up.

**a note on reset versus refused:** refused means nothing is listening. Reset means something answered and hung up. On my Mac nothing from kubectl was listening on 8080, so I expected refused. I got reset, which makes me think something else on the Mac was already on 8080. I have not tracked down what yet.

## Bonus: the forward worked and the password did not

The login page loaded. My password did not work.

I did not want to reset anything before I knew which account existed. Open WebUI keeps its users in a SQLite database inside the pod, and the image has Python but not the `sqlite3` command. So I asked Python, read only:

```bash
kubectl -n brasil exec deploy/open-webui -- python3 -c "import sqlite3; c=sqlite3.connect('/app/backend/data/webui.db'); print(c.execute('select email, role from user').fetchall())"
#    -> [('<my-email>', 'admin')]
```

Right email, admin account. Only the password was wrong. I backed up the database before writing to it:

```bash
kubectl -n brasil exec deploy/open-webui -- cp /app/backend/data/webui.db /app/backend/data/webui.db.bak
```

Then set a new password. Open WebUI stores a bcrypt hash, not the password, so the new one has to be hashed the same way. `getpass` keeps the password out of my shell history:

```bash
kubectl -n brasil exec -it deploy/open-webui -- python3 -c "import sqlite3,getpass,bcrypt; p=getpass.getpass('New password: '); h=bcrypt.hashpw(p.encode(),bcrypt.gensalt()).decode(); c=sqlite3.connect('/app/backend/data/webui.db'); n=c.execute('update auth set password=? where email=?',(h,'<my-email>')).rowcount; c.commit(); print('rows updated:',n)"
#    -> rows updated: 1
```

I logged in, picked qwen2.5, and asked it how you say good morning in Rio. It answered in Portuguese. The slang was a little off, but that is a problem for another post.

**worth knowing:** writing straight to an app's database is a last resort. Look first, back up second, change one row, and check that exactly one row changed.

## Final checklist: before you blame the cluster

```bash
# 1. Which machine am I on? Run the forward where the browser is.
hostname

# 2. What is the service actually called, and what port does it expose?
kubectl -n <namespace> get svc
#    -> use the name after the slash, and the port shown here

# 3. The command
kubectl -n <namespace> port-forward svc/<name> <local-port>:<service-port>

# 4. Did the pod restart? Restart the forward too.
kubectl -n <namespace> get pods
```

And what the errors meant, all in one place:

| What I saw | What it meant |
|---|---|
| Wrong remote port | I used the pod's port where the service's port goes |
| `may not have more than one slash` | I wrote the type twice |
| `services "..." not found` | Wrong name. kubectl was fine, the cluster said no |
| `ERR_CONNECTION_REFUSED` | Nothing listening. The forward died with the pod |
| `ERR_CONNECTION_RESET` | The forward was on the server, not my Mac |
| `broken pipe` in the terminal | The browser closing connections early. Harmless |

Next up, both of these tiles stop needing port-forward at all. They go behind a Cloudflare Tunnel with a login in front, Música first.
