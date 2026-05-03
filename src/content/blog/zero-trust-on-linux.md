---
title: "Zero Trust on Linux. explained like a real person."
description: "Every vendor has it on their website. Every job post wants it. Nobody can actually explain it. Let's fix that."
date: 2026-04-24
category: cybersecurity
readTime: 7
---

## Where the old model came from and why it completely fell apart

Picture it: it's 2003. Everyone works in the office. The servers are in the building. The firewall is the big scary wall between you and the internet, and if you're inside the wall you're basically family. Trusted. Welcome. Help yourself to the file share.

This is called perimeter-based security and for its time it made total sense. The logic was: we know who's inside, the bad guys are outside, and the wall keeps them out. Simple. Clean. Wrong, eventually, but clean.

Then a few things happened all at once. Cloud computing put servers outside the building. VPNs let people work from anywhere. Mobile devices meant your "trusted employee" was now connecting from a coffee shop on public wifi. SaaS apps meant company data lived in systems the company didn't even own. The perimeter just dissolved. There was no inside anymore.

But companies kept building thicker walls around a perimeter that didn't exist anymore. Which is like putting a really good lock on a door that has no walls around it. Classic.

The real nail in the coffin: attackers figured out the easiest way in wasn't through the firewall. It was a phishing email. One click from one tired employee and suddenly someone with bad intentions is inside the network, being treated like a trusted colleague, moving around freely. The firewall never saw it coming because the threat came from inside the house.

## What Zero Trust actually says

Zero Trust is built on one principle: **never trust, always verify.** That's it. That's the whole thing. Everything else is implementation details.

In the old model, trust came from location. You're inside the network? You're trusted. Zero Trust throws that out entirely. It does not care where your request comes from. Every single request gets verified. Every time. No free passes.

John Kindervag coined the term at Forrester in 2010. Core idea: treat every user, device, and network flow as untrusted by default. Verify identity explicitly. Use least-privilege access. And crucially: **assume breach.**

Those last two words are doing heavy lifting. Assume breach. Traditional security assumed the goal was keeping attackers out. Zero Trust assumes they're already in, or will be, and asks: how do we limit the damage? Instead of one big wall, you build a lot of small walls everywhere. So when something breaks through, it can't go anywhere.

## The three core principles, broken down like you're a person

**1. Verify explicitly.** Every access request gets checked against everything available: who are you, what device are you on, is that device patched and healthy, where are you connecting from, does this behavior look normal for you? It's not just "what's your password." It's a whole vibe check every single time.

In practice this means MFA is not optional anymore. It means short-lived credentials that expire instead of sessions that stay open for a week. It means checking device health before handing over access.

**2. Least privilege access.** You get exactly what you need to do your job and not one byte more. The developers in the RHEL 9 post could restart Apache. That was it. They couldn't touch `/etc/shadow`, modify users, or mess with system configs. That's least privilege doing its job.

**3. Assume breach.** Build every system like someone is already inside watching. Encrypt internal traffic because maybe someone is sniffing it. Log everything because you'll want receipts when something goes sideways. Segment the network so one compromised machine doesn't hand over the whole environment.

## How this maps to stuff you already do on Linux servers

If you've been following good sysadmin hygiene, you're already doing Zero Trust. You just weren't calling it that because the name is annoying.

**SSH key auth instead of passwords** is explicit verification. Cryptographic proof of identity instead of a string of characters someone can guess or steal from a sticky note.

**Scoped sudoers config** is least privilege. Scoped access by role, not "everyone gets sudo because it's easier."

**Disabling root login over SSH** is assume breach. Even if credentials get stolen, direct root access is blocked. Audit trail stays intact.

**firewalld zones** are network segmentation. Traffic only flows where it's supposed to. Everything else gets quietly dropped.

The difference between doing these things randomly and doing them as a Zero Trust strategy is intentionality. One is good habits. The other is a system designed to contain damage when something breaks.

## Hands-on: applying it to a real server right now

**Add MFA to SSH.** Key auth is solid. Key auth plus a one-time code is better.

```bash
# RHEL 9 / Rocky / CentOS Stream
sudo dnf install google-authenticator -y
google-authenticator  # run as the user, not root
```

Update `sshd_config` to require both factors:

```
ChallengeResponseAuthentication yes
AuthenticationMethods           publickey,keyboard-interactive
```

Keep your existing SSH session open while you test this in a second terminal. If you lock yourself out, you're not the first person to do it, but you will feel a certain type of way about it.

**Segment services with firewalld.** Your database should not be visible to the internet. Just no.

```bash
# remove mysql from public zone entirely
sudo firewall-cmd --zone=public --remove-service=mysql --permanent

# only allow your app server to reach it
sudo firewall-cmd --zone=public \
  --add-rich-rule='rule family="ipv4" source address="192.168.1.50" port port="3306" protocol="tcp" accept' \
  --permanent
sudo firewall-cmd --reload
```

**Log everything and actually look at it.**

```bash
sudo dnf install audit -y
sudo systemctl enable --now auditd

# watch sudo usage in real time
sudo journalctl -f | grep sudo

# check recent auth events
sudo ausearch -m USER_AUTH,USER_ACCT -ts recent
```

> **note:** Unexpected sudo usage outside business hours or from an account that doesn't normally use it is a signal worth investigating. That's the whole point of logging.

## What Zero Trust is NOT (vendor edition)

**It's not a product.** Every security vendor on earth will try to sell you a "Zero Trust solution." Some of those tools are genuinely useful. None of them are Zero Trust by themselves. You can buy all of them and still have a fundamentally broken architecture if the thinking isn't there.

**It's not all-or-nothing.** You don't flip a switch and achieve Zero Trust. You improve incrementally. MFA here, segmentation there, least privilege everywhere you can reach.

**VPN is not Zero Trust.** A VPN puts you inside the perimeter. That's literally the opposite of what Zero Trust is about.

**"Zero Trust means trusting nothing ever" is wrong.** It doesn't mean trust is never granted. It means trust is never assumed. Big difference. One is paranoia, the other is architecture.

## Final checklist: audit where you stand

```bash
# 1. root SSH login is off
sudo sshd -T | grep permitrootlogin

# 2. password auth is disabled
sudo sshd -T | grep passwordauthentication

# 3. MFA is configured
sudo grep pam_google_authenticator /etc/pam.d/sshd

# 4. firewalld zones are intentional
sudo firewall-cmd --get-active-zones
sudo firewall-cmd --zone=public --list-all

# 5. no unnecessary services exposed
sudo firewall-cmd --zone=public --list-services

# 6. sudo is scoped
sudo grep -r 'ALL=(ALL)' /etc/sudoers /etc/sudoers.d/

# 7. app processes not running as root
ps aux | grep -E 'httpd|nginx|mysql|postgres' | grep -v root

# 8. auditd is running
sudo systemctl status auditd

# 9. no dormant accounts with active permissions
sudo lastlog | grep -v 'Never logged in'
```

Nine checks. No enterprise software required. No security budget needed. Just understanding the model and applying it on purpose, one layer at a time. That's it. That's Zero Trust.