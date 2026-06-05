---
id: oic-ca-001-b
label: "Email-borne ransomware intrusion (Black Basta-style)"
type: cascade_archetype
domain: it
entry: "phishing email attachment"
terminal_impact: "domain-wide data encryption + recovery inhibition (availability loss)"
applies_when: "Windows domain · broad local-admin use · backups reachable from the network · thin endpoint detection"
sectors: sector-agnostic
dbir_pattern: system_intrusion
veris_entry: action.social.variety.phishing
veris_terminal: attribute.availability.variety.loss
anchor_incident: "Black Basta ransomware (active 2022–)"
tags: [ransomware, phishing, it-environment, backup-failure, lateral-movement]
---

## Scenario: email-borne ransomware intrusion

A phishing attachment becomes a domain-wide encryption event because the organization runs a flat
Windows estate with broad local admin, thin endpoint detection, and backups the attacker can reach.
The click is never the real problem — the outcome requires the chain below to complete.

**This is an IT-environment attack.** For an industrial/OT organization it threatens the business
and IT side and can force a *precautionary* OT shutdown, but it does **not** target the control
process itself. This is in contrast to OT cards (`oic-ca-010`, `oic-ca-011`), where the process is the target.

**Recognize this scenario** when several users receive unfiltered attachments, endpoints allow unapproved code/scripts to run, staff hold local admin, the network is flat enough for broad lateral movement, and backups sit online where ransomware can reach them.

### The cascade — collapsed to the decisive links

1. **Initial access & execution** — a phishing attachment runs a malicious macro/script that drops
   the loader.
   *Succeeds when:* attachments reach inboxes unfiltered, users aren't trained to spot lures, and the endpoint allows unapproved code/scripts to run. *(odds)*
2. **Foothold goes unnoticed** — the loader establishes C2 and persists while disabling defenses.
   *Succeeds when:* there's no behavior-based endpoint detection, and AV/firewall can be disabled without alerting. *(dwell)*
3. **Privilege escalation & credential access** — the attacker harvests credentials and gains admin/domain rights.
   *Succeeds when:* admin rights are broadly held and credentials are harvestable from memory or
   stores. *(spread)*
4. **Lateral movement** — admin access is reused across the estate via remote services.
   *Succeeds when:* the network is flat and remote services accept reused credentials without MFA.
   *(spread)*
5. **Inhibit recovery** — backups and shadow copies are deleted or encrypted, recovery is disabled.
   *Succeeds when:* backups are reachable from the production network rather than offline/immutable.
   *(size — sets whether recovery is even possible)*
6. **Encryption** — ransomware encrypts servers and endpoints domain-wide.
   *Succeeds when:* the attacker has reached enough of the estate with the privilege to encrypt.
   *(size)*

### Odds vs. size

Steps 1–4 change *how likely* the attack reaches its goal. Steps 5–6 set the *size* of the loss —
and step 5 is the pivot: with offline/immutable backups the outcome shifts from "pay or rebuild"
to "restore."

### Reducing this risk

_Grounded in ATT&CK mitigations for the techniques in the full flow. Candidates, not effectiveness
estimates._

**Reduce likelihood** — email filtering + user training (entry); behavior-based endpoint
detection / execution prevention (foothold, code execution); privileged-account management and
least privilege (escalation); MFA + network monitoring (lateral movement).

**Reduce impact** — offline / immutable / isolated backups (the dominant lever); network
segmentation to contain blast radius.

### Anchor (real incident)

Black Basta has run this pattern against organizations across many sectors since 2022 — phishing or
loader-based entry, living-off-the-land persistence and defense evasion, credential theft, lateral
movement, then recovery inhibition and encryption. Sources: MITRE ATT&CK (Black Basta), CISA/FBI
advisories, public IR reporting.
