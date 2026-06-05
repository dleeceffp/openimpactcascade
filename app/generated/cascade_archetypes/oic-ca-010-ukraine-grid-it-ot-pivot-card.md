---
id: oic-ca-010
label: "IT-to-OT pivot: remote manipulation of grid operations (Ukraine 2015-style)"
type: cascade_archetype
domain: ot
entry: "spearphishing attachment on the IT/business network"
terminal_impact: "remote operation of breakers → loss of control / process outage"
applies_when: "OT reachable from IT via remote access · single-factor VPN into SCADA · operator HMI remotely controllable · no out-of-band recovery for field devices"
sectors: "energy, utilities (pattern applies to any IT-connected OT)"
dbir_pattern: system_intrusion          # [note] DBIR is IT-centric; this is an OT campaign
veris_entry: action.social.variety.phishing
veris_terminal: attribute.availability   # [note] VERIS has no clean "loss of control" — availability is closest
anchor_incident: "2015 Ukraine power grid attack (Sandworm) — ~225,000 customers"
tags: [ot, ics, it-ot-pivot, remote-access, hmi-manipulation, loss-of-control, energy]
---

## Scenario: IT-to-OT pivot and remote manipulation of the process

A phishing email on the *business* network becomes a *physical* power outage because the OT network is reachable from IT through remote access, the operator HMI can be driven remotely, and the field
devices have no out-of-band path for recovery. Unlike ransomware, the target here is the **process itself** — the attacker operates the grid, they don't encrypt it.

**Recognize this scenario** when: the OT/SCADA network is reachable from IT, remote access into OT is single-factor, operator HMIs can be controlled remotely, ICS command messages aren't authenticated, and recovery of field devices depends on those same network paths.

### The cascade — collapsed to the decisive links

1. **Initial access (IT)** — a spearphishing attachment lands on the business network and steals
   credentials.
   *Succeeds when:* attachments reach staff unfiltered and credentials can be harvested. *(odds)*
2. **IT-to-OT pivot via remote access** — stolen credentials are used over the VPN to reach the SCADA/DMS network. **This is the bridge that makes a business-network phish a process attack.**
   *Succeeds when:* the OT network is reachable from IT and the remote access is single-factor (no MFA), so one stolen credential crosses the boundary. *(odds — the decisive gate)*
3. **Operate the process via HMI** — the attacker drives the operator HMI to issue breaker-open commands across substations.
   *Succeeds when:* the HMI can be controlled remotely and ICS command messages aren't authenticated, so spoofed/operator-issued commands are accepted. *(size — this is the impact)*
4. **Lock out the operators** — sessions/credentials are changed so staff can't reverse the commands.
   *Succeeds when:* there's no independent local/manual control path to override the remote session.
   *(size — extends the outage)*
5. **Inhibit recovery** — field-device (serial-to-Ethernet converter) firmware is overwritten and
   workstations are wiped, forcing slow on-site manual restoration; UPS reconfigured.
   *Succeeds when:* device firmware isn't integrity-protected and there's no out-of-band recovery
   path. *(size — the duration/magnitude driver)*
6. **Suppress response** — the customer call centre is flooded (telephonic DoS) to delay awareness.
   *Succeeds when:* response channels share the attack surface and have no fallback. *(dwell)*

### Odds vs. size

Step 2 (single-factor remote access into OT) is the decisive *likelihood* gate. Steps 3–5 set the
*size* and duration — and note the impact lever is **operational resilience** (manual control,
out-of-band recovery, firmware integrity), **not** data backup. Backups don't restore a bricked
substation converter.

### Reducing this risk

_Grounded in ATT&CK for ICS mitigations._

**Reduce likelihood** — MFA on all remote access into OT (the single highest-value control here);
IT/OT segmentation with a DMZ; restrict who/what can reach SCADA (network allowlists, least access);
authenticate ICS command messages so spoofed breaker commands are rejected; user training for the
phishing entry.

**Reduce impact** — out-of-band communications and **local/manual control** so operators can
override and restore without the compromised network; field-device firmware integrity / supply-chain
assurance; redundancy of critical services. (Data backup is largely irrelevant to this outcome.)

### Anchor (real incident)

On 23 December 2015, Sandworm used BlackEnergy3 (delivered by a phishing attachment) to gain the IT
foothold at three Ukrainian distribution utilities, then pivoted over VPN into the SCADA networks,
remotely operated operator HMIs to open breakers at ~50 substations, overwrote serial-to-Ethernet
gateway firmware and wiped systems to force manual recovery, and ran a telephonic DoS on the call
centres — leaving ~225,000 customers without power for 1–6 hours. Sources: SANS/E-ISAC Defense Use
Case (2016); CISA IR-ALERT-H-16-056-01; MITRE ATT&CK Campaign C0028.
