# Criminal Gang Active Directory Takeover – Canadian Energy Sector

## Context
- **Industry:** energy
- **Region:** Canada
- **Organization Size:** 2500
- **Generated:** 2026-06-18T06:01:32.380651

## Description
A financially-motivated criminal gang targets a mid-sized Canadian energy company (~2500 employees) with the objective of achieving full Active Directory compromise. The intrusion begins with a targeted phishing campaign against corporate users, establishes persistence via a commodity RAT or implant, then pivots through credential theft and lateral movement to reach a Domain Controller. The AD takeover enables ransomware staging or data extortion. Pattern is consistent with Black Basta, LockBit, and Akira affiliate activity observed against North American energy and utilities organisations.

**Scope:** incident

## Attack Actions (MITRE ATT&CK Techniques)

| ID | Tactic | Technique | Description | Predecessors | Confidence |
|----|--------|-----------|-------------|--------------|------------|
| n1 | Initial Access | T1566.002 - Spearphishing Link – Credential Harvesting Portal | Attackers send targeted phishing emails impersonat... | (entry) | ~ reported |
| n2 | Initial Access | T1078.002 - Valid Account – Use of Harvested Employee Credentials | Using credentials and session tokens captured via ... | n1 | ~ reported |
| n3 | Initial Access | T1133 - Remote Services – VPN / RDP into Corporate Network | The threat actor uses the compromised credentials ... | n2 | ~ reported |
| n4 | Credential Access | T1003.001 - OS Credential Dumping – LSASS Memory | Once on an internal Windows host, the attacker use... | n3 | ~ reported |
| n5 | Discovery | T1069.002 - Domain Account & Group Enumeration | The attacker runs BloodHound / SharpHound or nativ... | n3 | ~ reported |
| n6 | Credential Access | T1558.003 - Kerberoasting – Service Account Ticket Extraction | Using the BloodHound-identified service accounts w... | n4, n5 | ~ reported |
| n7 | Lateral Movement | T1550.002 - Lateral Movement – Pass-the-Hash / Pass-the-Ticket to Privileged Hosts | Using NTLM hashes dumped from LSASS and cracked Ke... | n6 | ~ reported |
| n8 | Persistence | T1053.005 - Scheduled Task / Service Persistence on Beachhead Host | On the compromised admin workstation or member ser... | n7 | ~ reported |
| n9 | Credential Access | T1003.006 - DCSync – Replication of All Domain Credentials | With Domain Admin or equivalent privileges gained ... | n7 | ~ reported |
| n10 | Credential Access | T1558.001 - Golden Ticket Forging – Persistent Privileged Access | Using the extracted KRBTGT hash, the attacker forg... | n9 | ~ reported |
| n11 | Impact | T1490 - Inhibit System Recovery – Disable VSS / Backup Services | Pre-ransomware staging: the attacker uses AD-wide ... | n10 | ~ reported |

**Branch points:** n3, n7
**Join points:** n6

## Logic Gates

- **AND**: n4, n5 → n6

## Targeted Assets
- Corporate Email / M365 Tenant
- SSL-VPN / RDP Gateway
- Employee Workstations
- IT Admin Workstations / Jump Servers
- Active Directory Domain Controllers
- SCADA / Historian Servers
- Backup Infrastructure

**Threat Actor:** Financially motivated criminal ransomware affiliate (consistent with Akira, Black Basta, or LockBit affiliate TTPs)

## MITRE Attack Flow (JSON)
The complete Attack Flow is available in JSON format conforming to the
[MITRE Attack Flow specification](https://github.com/center-for-threat-informed-defense/attack-flow).
