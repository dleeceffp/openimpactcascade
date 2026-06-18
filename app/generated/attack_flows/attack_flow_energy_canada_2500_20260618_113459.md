# Active Directory Takeover by Criminal Gang – Canadian Energy Sector

## Context
- **Industry:** energy
- **Region:** Canada
- **Organization Size:** 2500
- **Generated:** 2026-06-18T11:34:59.106782Z

## Description
A financially motivated criminal gang targets a mid-sized Canadian energy company (~2500 employees) with the goal of achieving full Active Directory compromise, enabling ransomware deployment or data extortion. The intrusion begins with a phishing campaign targeting corporate email users, proceeds through credential theft and internal reconnaissance, and culminates in domain controller takeover via DCSync or similar AD abuse.

**Scope:** incident

## Attack Actions (MITRE ATT&CK Techniques)

| # | Tactic | Technique | Name | Confidence |
|---|--------|-----------|------|------------|
| 1 | Initial Access | T1566.002 | Spearphishing Link | ~ reported |
| 2 | Execution | T1204.001 | User Execution – Malicious Link | ~ reported |
| 3 | Credential Access | T1539 | Steal Web Session Cookie / Adversary-in-the-Middle Credential Capture | ~ reported |
| 4 | Initial Access | T1078.004 | Valid Accounts – Cloud Accounts (M365 Foothold) | ~ reported |
| 5 | Execution | T1059.001 | Command and Scripting Interpreter – PowerShell (Stager Execution) | ~ reported |
| 6 | Credential Access | T1003.001 | OS Credential Dumping – LSASS Memory | ~ reported |
| 7 | Discovery | T1069.002 | Domain Account / Group Discovery | ~ reported |
| 8 | Lateral Movement | T1550.002 | Lateral Movement – Pass the Hash / Use Alternate Authentication Material | ~ reported |
| 9 | Credential Access | T1558.003 | Kerberoasting – Steal or Forge Kerberos Tickets | ~ reported |
| 10 | Credential Access | T1003.006 | DCSync – OS Credential Dumping | ~ reported |
| 11 | Credential Access | T1558.001 | Forge Kerberos Tickets – Golden Ticket | ~ reported |

## Targeted Assets
- Corporate email (Microsoft 365 / Entra ID)
- Domain-joined workstations
- Active Directory Domain Controllers
- Privileged service accounts (SCADA-adjacent)
- Internal file shares / SharePoint

## MITRE Attack Flow Format
This flow is in the native `.afb` (Attack Flow Binary) format compatible with the MITRE Attack Flow Builder.
