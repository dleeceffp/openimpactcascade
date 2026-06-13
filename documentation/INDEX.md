# OpenImpactCascade — Documentation

**OpenImpactCascade (OIC)** is a cyber risk quantification tool for small and medium businesses. It generates structured FAIR-methodology risk assessments — producing probability distributions and dollar-range estimates — to help organizations triage threats, evaluate control investments, and communicate risk in financial terms.

Repository: [github.com/dleeceffp/openimpactcascade](https://github.com/dleeceffp/openimpactcascade)

---

## Documents

### [User Guide](public/USER_GUIDE.md)

How to use the application. Covers all use cases, the two assessment paths, working through the questionnaire, interpreting results, the chat assistant, and notable features including cascade archetypes and threat-informed web search.

---

### [Deployment Guide](public/DEPLOYMENT_GUIDE.md)

How to deploy OIC to GCP Cloud Run. Covers developer environment setup (gcloud, Docker, Git Bash on Windows), GCP project prerequisites, the granular IAM permissions required, all secrets, the deploy script, local Docker execution, post-deployment verification, and updating a running service.

---

### [Application Reference](public/FLASK_README.md)

A site map of the running application. Every route, its template, and what it does. The complete file layout of the repository. All environment variables and feature flags with their defaults.

---

### [Simulation Engine](public/SIMULATION_ENGINE.md)

The statistical design of the Monte Carlo simulation engine. Covers why lognormal beats PERT for loss magnitude (and the research behind it), the Hubbard/Seiersen calibration method, the compound versus product simulation modes, the control lever model, and the full output statistics reference.

---

### [AI Design and Controls](public/AI_DESIGN_AND_CONTROLS.md)

AI vendor and model information, data privacy, what data the AI does and does not see, safeguards, operational data logging, architecture, and compliance considerations.

---

### [Layered Controls](public/LAYERED_CONTROLS_FEATURE.md)

The defense-in-depth feature: how the AND-gate probability model works, what the layered controls toggle does to the vulnerability estimate, and the mathematical basis for the 25% reduction heuristic.

---

## About

OpenImpactCascade is a beta product. Feedback and feature requests: [info@impactcascade.ca](mailto:info@impactcascade.ca)

Licensed under the Apache License, Version 2.0.
© 2026 FirstFire Productions — [impactcascade.ca](https://impactcascade.ca)
