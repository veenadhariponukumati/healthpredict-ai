# Publication Assets Checklist - v1.0.0

This is a planning document only. No images, GIFs, or video have been generated or captured - each item below lists what to capture, at what resolution, and where it goes in [README.md](README.md).

## Screenshots

| # | Filename | Resolution | Device | Placement in README | Purpose |
|---|---|---|---|---|---|
| 1 | `docs/assets/screenshot-login.png` | 1440×900 | Desktop | Screenshots section | Shows the login form and the three-role auth model |
| 2 | `docs/assets/screenshot-dashboard.png` | 1440×900 | Desktop | Screenshots section | Shows the summary/risk-distribution dashboard |
| 3 | `docs/assets/screenshot-patient-list.png` | 1440×900 | Desktop | Screenshots section | Shows patient management list view |
| 4 | `docs/assets/screenshot-patient-detail.png` | 1440×900 | Desktop | Screenshots section | Shows a single patient's record and history |
| 5 | `docs/assets/screenshot-prediction.png` | 1440×900 | Desktop | Screenshots section | Shows a prediction result with the SHAP explanation chart - the most technically interesting screen |
| 6 | `docs/assets/screenshot-workflow.png` | 1440×900 | Desktop | Screenshots section | Shows a workflow's status/detail (Temporal + n8n execution) |
| 7 | `docs/assets/screenshot-audit.png` | 1440×900 | Desktop | Screenshots section | Shows the audit log (RBAC/compliance angle) |
| 8 | `docs/assets/screenshot-health.png` | 1440×900 | Desktop | Screenshots section (optional, can go in LOCAL_SETUP.md instead) | Shows `/health`/`/ready` output - demonstrates operational maturity to engineer/CTO readers |

Capture with the browser window at 1440×900 (or crop to that ratio afterward) so all screenshots are visually consistent. Use the seeded demo accounts (`admin@test.com`, `clinician@test.com`, `viewer@test.com` / `Test123!`) and synthetic patient data only - never real data, which is a non-issue here since only synthetic data exists.

## Architecture Assets

| # | Filename | Resolution | Placement in README | Purpose |
|---|---|---|---|---|
| 9 | `docs/assets/architecture-diagram.png` | 1600×1200 (or SVG) | Replace/supplement the ASCII diagram in "Architecture at a Glance" | Rendered version of the existing ASCII service diagram - cleaner for recruiters skimming on GitHub |
| 10 | `docs/assets/workflow-diagram.png` | 1600×1200 (or SVG) | New subsection under Architecture, or in `docs/WORKFLOWS.md` | Shows the Temporal + n8n care-coordination flow: prediction → workflow trigger → Temporal orchestration → n8n webhook → (simulated) notification. Label the final step "simulated" directly on the diagram - do not let the diagram imply a real integration. |

## Media

| # | Filename | Duration | Placement in README | Purpose |
|---|---|---|---|---|
| 11 | `docs/assets/demo.gif` | 20–30s | Top of README, right after the title/badges | Fast, silent loop for GitHub's inline renderer - login → prediction → workflow trigger. Keep under ~10MB so it renders inline without lazy-load issues. |
| 12 | Demo video (YouTube/Loom link, not committed to Git) | 2–3 min | Linked from README ("Watch the full walkthrough →") and from the GitHub Release notes | Full narrated walkthrough - see recording plan below. Do not commit a video file directly to Git; link out instead. |

## Demo Recording Plan (2–3 minutes)

Keep narration factual - state plainly what's real and what's simulated when you reach the workflow section. Do not describe the notification step as "sending a text" or "notifying the care team" without the word "simulated" attached.

```
0:00  Login as clinician (admin@test.com / Test123!)
0:15  Dashboard - risk distribution, summary stats
0:35  Patient Management - list, open a patient detail
1:00  Create or open a prediction - show the risk score
1:20  SHAP Explanation - walk through 2-3 top contributing features
1:50  Trigger a workflow (via API call or existing workflow) - show it reach Temporal
2:10  Workflow detail page - show status, and the n8n step
      Narrate: "This step is simulated - n8n returns a mock response instead of
      sending a real SMS/email/appointment booking."
2:35  Audit log - show the recorded actions
2:50  Known Limitations - one sentence: "Full list of verified limitations is in
      KNOWN_LIMITATIONS.md, including the simulated notification step."
3:00  End
```

If you record only a GIF (no video), compress the above into the 20–30s version: login → prediction → workflow trigger, no narration needed since GIFs are silent.

## Status

Nothing in this checklist has been created yet. All 12 items are outstanding.
