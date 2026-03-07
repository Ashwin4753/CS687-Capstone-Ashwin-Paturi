# SynchroMesh

**SynchroMesh** is an agentic design–code governance system that detects UI drift in frontend repositories, maps hard-coded styling to design tokens, applies bounded-autonomy governance, and generates auditable modernization outputs.

The system integrates drift detection, token mapping, governance workflows, and evaluation into a single interactive dashboard.

SynchroMesh demonstrates how **agentic orchestration can safely assist software modernization workflows** while maintaining transparency, explainability, and human oversight.

---

# Table of Contents

- [Project Overview](#project-overview)
- [Problem Statement](#problem-statement)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Core Workflow](#core-workflow)
- [Technology Stack](#technology-stack)
- [How the System Works](#how-the-system-works)
- [Dashboard Modules](#dashboard-modules)
- [Evaluation Framework](#evaluation-framework)
- [Mock Mode vs Real Mode](#mock-mode-vs-real-mode)
- [Setup Instructions](#setup-instructions)
- [Environment Variables](#environment-variables)
- [Running the Project](#running-the-project)
- [Using the Dashboard](#using-the-dashboard)
- [Recommended Demo Flow](#recommended-demo-flow)
- [Supported Repository Scenarios](#supported-repository-scenarios)
- [Outputs Generated](#outputs-generated)
- [Governance Model](#governance-model)
- [Known Limitations](#known-limitations)
- [Future Enhancements](#future-enhancements)
- [Research / Capstone Value](#research--capstone-value)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

# Project Overview

SynchroMesh is an **agentic orchestration platform** designed to detect and resolve design–code drift in frontend applications.

Modern UI codebases frequently diverge from their design systems due to:

- hard-coded visual values
- outdated tokens
- inconsistent styling practices
- rapid feature development
- missing design system governance

SynchroMesh detects these inconsistencies and proposes governed token replacements.

The platform integrates:

- **drift detection**
- **token mapping**
- **human-in-the-loop approval**
- **automated patch generation**
- **evaluation metrics**
- **auditability and explainability**

All results are surfaced through a structured governance dashboard.

---

# Problem Statement

Frontend systems frequently accumulate **visual drift** between implementation and the intended design system.

Examples include:

- hard-coded colors such as `#3b82f6`
- inline styles such as `margin: 12px`
- duplicated styling logic
- outdated design tokens
- inconsistent component styling

These issues lead to:

- inconsistent UI behavior
- reduced maintainability
- difficult modernization
- higher refactoring risk

SynchroMesh addresses this problem through a **governed agentic workflow** that identifies, evaluates, and safely applies design token replacements.

---

# Key Features

## Design Drift Detection

Scans frontend repositories to detect:

- hard-coded colors
- RGB / RGBA values
- spacing values (`px`, `rem`, `%`)
- inline styles

## Token Mapping

Maps detected drift values to design tokens from the token source.

## Governance Workflow

Implements bounded autonomy using policy-based approval rules.

Changes are classified as:

- LOW risk
- MEDIUM risk
- HIGH risk

## Human-in-the-Loop Review

Developers can review recommendations before they are applied.

## Automated Patch Generation

Approved changes are converted into:

- diffs
- patch outputs
- PR draft content

## Evaluation Metrics

The system tracks modernization metrics including:

- parity score
- token coverage
- drift distribution
- component impact
- explainability metrics

## Interactive Dashboard

The Streamlit dashboard provides structured views for:

- drift detection
- approval review
- synchronization results
- reasoning traces
- evaluation reports

---

# System Architecture

SynchroMesh is organized into modular layers.

## Agent Layer

- **Archaeologist Agent**
- **Stylist Agent**
- **Syncer Agent**

## Core Layer

- orchestrator
- context store
- state management

## Interaction Layer

- governance dashboard
- approval interface
- reasoning panel
- visualization components

## Integration Layer

- GitHub MCP client
- Figma MCP client

## Evaluation Layer

- parity calculator
- log analyzer
- validator
- modernization report generator

---

# Project Structure


synchromesh/
│
├── agents/
│ ├── archaeologist.py
│ ├── stylist.py
│ └── syncer.py
│
├── core/
│ ├── orchestrator.py
│ ├── context_store.py
│ └── state.py
│
├── evaluation/
│ ├── parity_calculator.py
│ ├── log_analyzer.py
│ ├── validator.py
│ ├── modernizationreportgenerator.py
│ ├── reports/
│ ├── traces/
│ └── data_exports/
│
├── integration/
│ ├── figma_mcp_client.py
│ └── github_mcp_client.py
│
├── interaction/
│ ├── approval_gate.py
│ └── dashboard/
│ ├── app.py
│ ├── visualizer.py
│ ├── governance_ui.py
│ └── reasoning_panel.py
│
├── config/
│ └── settings.yaml
│
├── outputs/
├── logs/
├── main.py
├── requirements.txt
└── README.md


---

# Core Workflow

The pipeline executes the following stages:

1. Repository is provided through the dashboard
2. Files are discovered in the project
3. Hard-coded styling is detected
4. Design tokens are loaded
5. Drift findings are mapped to tokens
6. Risk classification is applied
7. Governance rules determine approval requirements
8. Users approve or reject recommendations
9. Approved changes are applied
10. Patches, metrics, and reports are generated

---

# Technology Stack

## Programming Language

- Python 3.11+

## UI Framework

- Streamlit

## Configuration

- YAML
- environment variables

## Integrations

- MCP-compatible GitHub server
- MCP-compatible Figma server

## Data Handling

- JSON
- CSV
- Markdown reports

---

# How the System Works

## Archaeologist Agent

Detects hard-coded styling patterns using pattern matching techniques.

Examples:


#3b82f6
rgb(59,130,246)
12px
margin: 12px


The agent also performs lightweight dependency analysis.

---

## Stylist Agent

Maps detected values to design tokens.

Each recommendation contains:

- file path
- line number
- original value
- proposed token
- replacement value
- risk classification
- reasoning
- confidence score
- change ID

---

## Approval Gate

Implements governance policies such as:

- auto-approve low risk changes
- require approval for medium/high risk
- block restricted directories
- limit number of files per synchronization

---

## Syncer Agent

Applies approved replacements and generates:

- unified diffs
- patch summaries
- PR draft content

---

# Dashboard Modules

## Dashboard

Displays high-level modernization metrics.

Includes:

- parity score
- risk distribution
- governance statistics
- evaluation insights

---

## Detected Drift

Primary operational interface.

Shows:

- drift findings
- affected files
- risk levels
- suggested actions
- approval panel

---

## Sync Workflow

Displays:

- generated patches
- PR draft content
- synchronization statistics

---

## Review Logs

Displays:

- run metadata
- reasoning traces
- explainability statistics

---

## Documentation

Displays:

- modernization reports
- evaluation summaries
- exported artifacts

---

## Settings

Displays current configuration values such as:

- repository root
- Figma file ID
- GitHub owner
- GitHub repository

---

# Evaluation Framework

SynchroMesh evaluates modernization results using several metrics.

## Runtime Metrics

- parity score
- drift instances
- recommendations generated
- patches applied
- risk distribution

## Explainability Metrics

- trace entries
- confidence scores
- action counts by agent

## Analysis Metrics

- token coverage
- drift hotspots
- component impact ranking

---

# Mock Mode vs Real Mode

SynchroMesh supports two execution modes.

## Mock Mode

Recommended for demos and presentations.

Uses built-in mock clients for GitHub and Figma.

Advantages:

- deterministic results
- no external dependencies
- stable execution

---

## Real Mode

Uses MCP integrations with GitHub and Figma.

Requires:

- valid tokens
- MCP server availability
- compatible tool APIs

Real mode behavior depends on the MCP server configuration.

---

# Setup Instructions

## Clone Repository


git clone <repository-url>
cd synchromesh


## Create Virtual Environment


python -m venv .venv
source .venv/bin/activate


## Install Dependencies


pip install -r requirements.txt


---

# Environment Variables

Example `.env` configuration:


FIGMA_ACCESS_TOKEN=your_figma_token
GITHUB_TOKEN=your_github_token
GOOGLE_API_KEY=your_google_api_key
SYNCHROMESH_MODE=mock


---

# Running the Project

## Mock Mode


export SYNCHROMESH_MODE=mock
python main.py


---

## Real Mode


export SYNCHROMESH_MODE=real
python main.py


---

Open the dashboard at:


http://localhost:8501


---

# Using the Dashboard

Typical workflow:

1. Start the pipeline
2. Review dashboard summary
3. Navigate to **Detected Drift**
4. Approve recommended changes
5. Re-run pipeline with approvals
6. Review patches and logs
7. Export modernization reports

---

# Recommended Demo Flow

1. Start SynchroMesh in **mock mode**
2. Run the pipeline
3. Show dashboard metrics
4. Navigate to **Detected Drift**
5. Approve a few changes
6. Re-run synchronization
7. Show patch results and PR draft
8. Show reasoning logs
9. Show evaluation results

---

# Supported Repository Scenarios

Best suited for frontend projects with:

- React
- JSX / TSX
- CSS / SCSS
- component-based UI architectures

Example repositories used during testing include:

- `flatlogic/react-dashboard`
- `bulletproof-react`

---

# Outputs Generated

SynchroMesh writes structured outputs including:


outputs/
drift_report.json
recommendations.json
approved_changes.json
metrics.json
patches.json


Evaluation artifacts include:


evaluation/reports/
evaluation/traces/
evaluation/data_exports/


---

# Governance Model

Changes are classified by risk.

## LOW Risk

- exact token match
- safe replacement
- optionally auto-approved

## MEDIUM Risk

- approximate token match
- requires approval

## HIGH Risk

- unknown mapping
- inline style
- requires manual review

---

# Known Limitations

- drift detection is regex-based
- approximate token matching is limited
- MCP integrations depend on server compatibility
- dependency analysis is lightweight
- dashboard is designed for demonstration rather than production deployment

---

# Future Enhancements

Potential improvements include:

- AST-based style detection
- stronger token similarity matching
- real GitHub PR automation
- component ownership analysis
- design screenshot comparison
- advanced visualization features
- expanded governance rules

---

# Research / Capstone Value

SynchroMesh demonstrates:

- agentic orchestration
- governed autonomy
- explainability-aware software tooling
- modernization pipelines
- human-AI collaborative workflows

It serves as both an engineering artifact and a research exploration of **safe AI-assisted code transformation**.

---

# Troubleshooting

## Dashboard crashes

Verify:

- Python environment is activated
- dependencies are installed
- environment variables are configured

## MCP connection issues

Switch to mock mode if MCP servers are unavailable.


export SYNCHROMESH_MODE=mock


## No drift detected

Ensure the repository contains detectable hard-coded styling values.

---

# License

MIT License

---

# Author

Ashwin Shastry Paturi  
SynchroMesh — Agentic Design-Code Governance Dashboard