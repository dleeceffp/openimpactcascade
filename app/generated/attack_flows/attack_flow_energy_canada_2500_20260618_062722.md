# Active Directory Takeover by Criminal Gang — Canadian Energy Sector

## Context
- **Industry:** energy
- **Region:** Canada
- **Organization Size:** 2500
- **Generated:** 2026-06-18T06:27:22.300905

## Description
A financially motivated criminal gang targets a mid-sized Canadian energy operator (~2500 employees). The campaign begins with a spearphishing lure crafted around energy-sector themes (e.g., regulatory filings, NERC CIP compliance documents), establishes a foothold via a commodity loader, pivots through credential harvesting and Kerberos abuse, and ultimately seizes control of Active Directory to deploy ransomware across OT-adjacent infrastructure.

**Scope:** incident

## Attack Actions (MITRE ATT&CK Techniques)

| ID | Tactic | Technique | Description | Predecessors | Confidence |
|----|--------|-----------|-------------|--------------|------------|
| n1 | Initial Access | T1566.001 - Spearphishing Attachment — Energy-Themed Lure | Attackers send targeted emails to IT and finance s... | (entry) | ~ reported |
| n2 | Execution | T1204.002 - User Execution — Malicious Office Macro | A targeted employee opens the attachment and enabl... | n1 | ~ reported |
| n3 | Credential Access | T1003.001 - OS Credential Dumping — LSASS Memory | After establishing persistence and disabling local... | n2 | ~ reported |
| n4 | Discovery | T1087.002 - Domain Account Discovery | Using harvested credentials, the attacker enumerat... | n3 | ~ reported |
| n5 | Credential Access | T1558.003 - Kerberoasting — Service Account Hash Extraction | The attacker requests Kerberos TGS tickets for ser... | n4 | ~ reported |
| n6 | Lateral Movement | T1550.002 - Lateral Movement via Pass-the-Hash to IT Admin Jump Host | Using cracked or harvested NTLM hashes, the attack... | n5 | ~ reported |
| n7 | Lateral Movement | T1021.001 - Remote Services — RDP to Domain Controller | From the privileged jump host, the attacker uses R... | n6 | ~ reported |
| n8 | Credential Access | T1003.006 - DCSync — Domain Credential Replication | With Domain Admin rights on the DC, the attacker p... | n7 | ~ reported |
| n9 | Persistence | T1136.002 - Create/Modify Domain Account — Backdoor Admin | The attacker creates a hidden Domain Admin account... | n8 | ~ reported |
| n10 | Impact | T1490 - Inhibit System Recovery — Shadow Copy Deletion via GPO | Using Domain Admin access, the attacker deploys a ... | n9 | ~ reported |
| n11 | Impact | T1486 - Data Encrypted for Impact — Ransomware Deployment via GPO | The attacker pushes ransomware (e.g., BlackCat/ALP... | n10 | ~ reported |

## Targeted Assets
- Corporate email infrastructure
- Domain-joined employee workstations
- Active Directory Domain Controllers
- IT/OT jump hosts
- SCADA/historian service accounts
- Energy management and NERC CIP compliance systems
- Backup and recovery infrastructure

**Threat Actor:** Financially motivated criminal ransomware gang (e.g., ALPHV/BlackCat, Play, or LockBit affiliate) targeting critical infrastructure for double-extortion

## MITRE Attack Flow (JSON)
The complete Attack Flow is available in JSON format conforming to the
[MITRE Attack Flow specification](https://github.com/center-for-threat-informed-defense/attack-flow).
