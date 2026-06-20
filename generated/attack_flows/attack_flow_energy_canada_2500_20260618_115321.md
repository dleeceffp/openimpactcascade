# Active Directory Takeover of Canadian Energy Utility by Criminal Gang

## Context
- **Industry:** energy
- **Region:** Canada
- **Organization Size:** 2500
- **Generated:** 2026-06-18T11:53:21.122569Z

## Description
A financially motivated criminal gang targets a mid-sized Canadian energy company (~2500 employees) with the objective of achieving full Active Directory compromise, likely to deploy ransomware or extort the organization. The intrusion begins with spearphishing against IT/OT staff, establishes persistent foothold via credential theft, escalates through AD abuse, and culminates in domain controller compromise. This pattern is consistent with ransomware operators (e.g., LockBit, Black Basta affiliates) known to target North American energy sector organizations.

**Scope:** incident

## Attack Actions (MITRE ATT&CK Techniques)

| # | Tactic | Technique | Name | Confidence |
|---|--------|-----------|------|------------|
| 1 | TA0001 | T1566.002 | Spearphishing Link to Credential Harvesting Page | ~ reported |
| 2 | TA0001 | T1078.002 | Valid Account Use via Stolen Credentials | ~ reported |
| 3 | TA0001 | T1133 | Remote Services Access via VPN/RDP | ~ reported |
| 4 | TA0006 | T1003.001 | LSASS Memory Credential Dumping | ~ reported |
| 5 | TA0007 | T1018 | Internal Network and AD Enumeration | ~ reported |
| 6 | TA0006 | T1558.003 | Kerberoasting — Service Account Ticket Extraction | ~ reported |
| 7 | TA0008 | T1550.002 | Lateral Movement to Privileged Host via Pass-the-Hash | ~ reported |
| 8 | TA0006 | T1003.006 | DCSync Attack — Domain Credential Replication | ~ reported |
| 9 | TA0006 | T1558.001 | Golden Ticket Forging | ~ reported |
| 10 | TA0003 | T1053.005 | Scheduled Task Persistence on Domain Controller | ? speculative |
| 11 | TA0040 | T1490 | Inhibit System Recovery — Backup and Shadow Copy Deletion | ~ reported |

## Targeted Assets
- Corporate VPN / Remote Access Gateway
- Active Directory Domain Controllers
- IT Privileged Admin Workstations
- Domain Service Accounts
- Employee Email Accounts
- Internal Jump Servers
- Backup Infrastructure

## MITRE Attack Flow Format
This flow is in the native `.afb` (Attack Flow Binary) format compatible with the MITRE Attack Flow Builder.
