---
id: oic-ca-001
label: "Flat-network ransomware via commodity phish"
type: cascade_archetype
entry: "phishing email (malicious macro or link)"
terminal_impact: "ransomware encryption — loss of availability across servers"
applies_when: "flat internal network · backups reachable from production · shared/over-privileged admin"
sectors: "sector-agnostic; common in mid-market"
dbir_pattern: system_intrusion
veris_entry: action.social.variety.phishing
veris_terminal: attribute.availability.variety.destruction
anchor_incident: "Maastricht University, 2019 (Clop / TA505)"
tags: [ransomware, phishing, flat-network, backup-failure, lateral-movement, dwell-time]
---

## Scenario: flat-network ransomware via commodity phish

A routine phishing email turns into a domain-wide ransomware event because the
organization has thin internal detection, a flat network, and backups that sit
where ransomware can reach them. The click is never the real problem — the damage
requires a chain of controls to fail in sequence.

**Recognize this scenario** when an organization combines several of: exposure to
phishing at email/endpoint, little or no internal monitoring or EDR, a flat network
allowing broad lateral movement, shared or over-privileged admin accounts, and
backups kept online where they can be encrypted. Any one of these alone is usually
survivable; together they form the cascade.

### The cascade — each link must fail for the next to be reached

1. **Initial access** — phishing email runs a malicious macro/payload.
   Broken by: email filtering, blocked macros, user awareness. *(changes the odds)*
2. **Foothold goes unnoticed** — malware beacons out and no alert fires.
   Broken by: endpoint detection / EDR. *(changes the odds)*
3. **Long undetected dwell** — the attacker roams the network for weeks.
   Broken by: network and log monitoring + segmentation. *(odds, and how far it spreads)*
4. **Privilege escalation** — the attacker exploits an unpatched system.
   Broken by: patch and vulnerability management. *(changes the odds — but see branching)*
5. **Domain takeover** — admin credentials are harvested, full control gained.
   Broken by: admin tiering, MFA on admin accounts, least privilege. *(limits how far it spreads)*
6. **Defenses disabled** — antivirus is killed just before encryption.
   Broken by: tamper-resistant endpoint protection. *(reduces the damage)*
7. **Encryption + backups destroyed** — ransomware hits servers and the online backups.
   Broken by: offline / immutable / isolated backups. *(this sets the SIZE of the loss)*

### Two things to help a user see

- **Branching.** Step 4 had alternatives — other unpatched hosts, stolen credentials,
  more than one way up. Fixing a single weakness doesn't close the route; the attacker
  reroutes. Resilience comes from breaking the chain in several places, not just one.
- **Odds vs. size.** Detection and segmentation (steps 2–3) change *how likely* the attack
  is to succeed. Backups (step 7) barely change the odds but change the *size* of the loss
  by an order of magnitude — pay-and-rebuild versus restore-and-move-on. These are different
  decisions and worth weighing separately.

### Anchor (real incident)

In 2019 a phishing email at Maastricht University led, nine weeks later, to Clop ransomware
encrypting 267 servers — including the online backups — and a roughly €200,000 ransom.
Investigators traced it to exactly this chain: no monitoring, a flat network, an unpatched
server used for escalation, and backups left reachable.
