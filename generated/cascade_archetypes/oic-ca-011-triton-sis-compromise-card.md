---
id: oic-ca-011
label: "Safety-instrumented-system compromise (TRITON/TRISIS-style)"
type: cascade_archetype
domain: ot
entry: "access to the OT/process network → SIS engineering workstation"
terminal_impact: "malicious logic on the safety controller → loss of safety function"
applies_when: "SIS reachable from the OT network · SIS not isolated from the DCS · controller key switch left in PROGRAM mode · engineering workstation not locked down"
sectors: "oil & gas, chemical, energy, water (any process protected by a safety-instrumented system)"
dbir_pattern: system_intrusion          # [note] DBIR/VERIS don't model safety impact; closest pattern only
veris_entry: "[manual] no clean VERIS vector for OT engineering-workstation access"
veris_terminal: "[manual] VERIS has no 'loss of safety' attribute — IT-centric frameworks miss this"
anchor_incident: "TRITON / TRISIS (2017), Saudi petrochemical facility — first SIS-targeting attack"
tags: [ot, ics, safety, sis, engineering-workstation, loss-of-safety, oil-gas, chemical]
---

## Scenario: compromise of the safety-instrumented system

An attacker who reaches the safety controllers can disable the layer that exists to prevent physical harm — so that a separate process attack could cause damage without the safety system tripping. The
target is not data and not even production uptime; it is **safety**. This is the OT-unique impact that has no IT analogue, and the reason IT-centric risk frameworks (DBIR/VERIS) don't capture it.

**Recognize this scenario** when: the SIS is reachable from the broader OT network, the SIS shares paths with the DCS rather than being isolated, the controller key switch is left in PROGRAM mode,
and the SIS engineering workstation isn't locked down.

### The cascade — collapsed to the decisive links

1. **Reach the OT/process network** — the attacker establishes a foothold inside OT (via IT-to-OT pivot or remote/engineering access).
   *Succeeds when:* OT is reachable from outside the process network and access isn't tightly restricted. *(odds)*
2. **Compromise the SIS engineering workstation** — the host running the controller-programming software is taken over.
   *Succeeds when:* the engineering workstation isn't hardened or isolated, and device/software authentication isn't enforced. *(odds)*
3. **Reach the safety controllers** — the attacker discovers and connects to the SIS controllers.
   *Succeeds when:* the SIS isn't network-isolated from the DCS, so a host on the control network
   can talk to the safety controllers. *(odds)*
4. **Controller in PROGRAM mode** — the physical key switch is left in PROGRAM (not RUN/locked), permitting a logic download. **This is the decisive physical prerequisite.**
   *Succeeds when:* the key switch is left in PROGRAM mode during normal operation rather than locked in RUN. *(odds)*
5. **Download malicious logic to the SIS** — the controller is reprogrammed over the engineering protocol.
   *Succeeds when:* gates 2–4 hold; the controller accepts a program download. *(size — the safety-compromise action)*
6. **Disable the safety function** — the SIS is subverted so it won't trip on a hazardous condition, removing the protection layer.
   *Succeeds when:* the SIS is the *only* protection layer — no independent/diverse safeguard backs
   it up. *(size — loss of safety)*

### Odds vs. size

Gates 3–4 (SIS not isolated; key switch left in PROGRAM mode) are the decisive *likelihood* gates —
and gate 4 is a procedural/physical control, not a software one. Gate 6 sets the *size*: the loss is catastrophic only if the SIS is the sole safeguard. The impact lever is **independent protection layers**, not anything resembling backups or EDR.

### Reducing this risk

_Grounded in ATT&CK for ICS mitigations, plus the vendor's own procedural guidance._

**Reduce likelihood** — isolate the SIS from the DCS and IT (network segmentation is the big one); restrict and authenticate access to the SIS and its engineering workstation (access management, device/software authentication, network allowlists); and the procedural control the vendor itself stressed — **keep the controller key switch in RUN/locked**, in PROGRAM only during supervised maintenance.

**Reduce impact** — keep the SIS an *independent* protection layer (don't let it be programmable from the same path as the DCS), and retain **mechanical/physical safeguards** (relief valves, interlocks) that act even if the SIS logic is subverted. Defense-in-depth of *diverse* safety layers is the magnitude control.

### Anchor (real incident)

In 2017, attackers reached the OT network of a Middle East petrochemical facility, took over a Triconex SIS engineering workstation, reverse-engineered the proprietary TriStation protocol, and used it to download malicious logic to Schneider Triconex safety controllers — possible only because the controller key switch was in PROGRAM mode. The intent was to disable the safety function so a
process attack could cause physical damage; it was discovered when the SIS detected an anomaly and tripped the plant to a safe state. It was the first known cyberattack on a safety-instrumented system. Sources: Dragos (TRISIS), FireEye/Mandiant (TRITON), Schneider Electric advisory, MITRE ATT&CK for ICS (Software S0013).
