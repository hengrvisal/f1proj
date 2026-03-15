# F1 AI Platform — Project Summary

## Concept Overview

A fan-facing AI platform that lets F1 enthusiasts ask questions ranging from casual to deeply analytical, with answers grounded in real telemetry data, historical race data, and contextual sources like press conferences and team radio. Positioned at the intersection of two portfolio ideas: **Driver DNA (driving style fingerprinting)** and **F1 Race Debrief AI (RAG-powered analyst)**.

The core insight: F1's fanbase has exploded post-Drive to Survive, but most fans don't have the technical vocabulary to dig into the data themselves. This platform bridges that gap — giving anyone a data-backed, cited answer to any F1 question.

---

## Problem Being Solved

- Existing F1 stats sites answer predefined questions only
- General AI (ChatGPT, etc.) hallucinates F1 facts with no grounding in real data
- Fans who want deep analytical answers have no accessible tool
- The telemetry and historical data exists but is inaccessible to non-technical users

---

## Target Users

- Casual F1 fans who became interested post-Drive to Survive
- Fantasy F1 players who want data-backed decisions
- F1 content creators and journalists
- Hardcore fans who want to go deeper than commentary provides

---

## Suggested Name Ideas

- **PitWall AI** — strategic connotation, F1-native
- **BoxBox** — radio call for pit in, memorable
- **Telemetry** — clean, descriptive

---

## Core Features

### 1. Freeform Chat Interface
Users ask plain English questions and receive data-backed answers with cited sources. Examples:
- *"Why did Verstappen's pace drop in stint 2 at Silverstone 2024?"*
- *"Has Ferrari made this strategy mistake at Monaco before?"*
- *"How does Leclerc perform in the rain compared to his dry weather pace?"*

### 2. Driver DNA Visualisation
- Corner-by-corner telemetry fingerprinting (throttle, brake, speed, gear traces)
- Driver style clustering — which drivers are most similar to each other?
- Quali vs. race pace gap analysis
- Comparisons across circuits and seasons

### 3. Optimal Lap Constructor
- For a given circuit, find the best mini-sector from each driver across a race weekend
- Stitch into a theoretical "ghost lap" — the fastest physically possible lap
- Compare against actual pole lap to quantify performance left on table

### 4. Tyre Degradation Modelling
- Model actual deg curves per compound, circuit, and driver
- Strategy simulator: input race scenario → suggested optimal pit windows

### 5. Text-to-SQL Query Engine
- Natural language → SQL queries against structured historical database
- *"Which driver has the best wet weather win rate at street circuits since 2010?"*
- *"What's the average pit stop variance per constructor at Monaco?"*

---

## Architecture — Three Layers

### Layer 1 — Data Foundation (SQL + Python)
- Ingest from FastF1 and OpenF1 APIs
- Clean, normalise, and store in PostgreSQL
- Covers: lap times, sector deltas, tyre stints, pit windows, driver standings, weather
- Scope: Start with 2023 and 2024 seasons only — depth over breadth

### Layer 2 — Intelligence Layer (ML)
- Process telemetry into meaningful features:
  - Corner-by-corner throttle/brake/steering profiles
  - Tyre degradation curves
  - Wet vs. dry performance deltas
  - Undercut/overcut success modelling
- Store derived insights as structured data AND embeddable text summaries
- Tools: scikit-learn, pandas, FastF1, MLflow or Weights & Biases for experiment tracking

### Layer 3 — RAG + Chat Layer (LLM)
- Embed and index:
  - ML-derived insights from Layer 2
  - Race reports and post-race summaries
  - Press conference transcripts (fia.com, formula1.com)
  - Team radio key moments
- Vector store: **pgvector** (extends existing Postgres — elegant choice)
- LLM: Anthropic Claude API (claude-sonnet-4-6)
- Routing logic: factual query → Text-to-SQL | analytical/contextual query → RAG
- Framework: LangChain or LlamaIndex

---

## Tech Stack

| Layer | Technology |
|---|---|
| Data ingestion | Python, FastF1, OpenF1 API, Ergast/Jolpica |
| Database | PostgreSQL + pgvector |
| ML/Analytics | pandas, scikit-learn, MLflow |
| LLM / RAG | Anthropic Claude API, LangChain or LlamaIndex |
| Backend API | FastAPI |
| Frontend | Next.js + React, Recharts or D3 for telemetry visualisation |
| Deployment | Vercel (frontend), Railway or Render (backend) |

---

## Data Sources

| Source | What It Provides |
|---|---|
| **FastF1** (Python library) | Telemetry, tyre data, sector times, team radio, weather |
| **OpenF1 API** | Real-time + historical data, REST-based, clean |
| **Jolpica API** | Full historical results back to 1950 (maintained Ergast fork) |
| **f1db** | Comprehensive open structured database |
| **FIA / formula1.com** | Press conference transcripts, race reports (scrape) |

---

## Phased Build Plan

### Phase 1 — Data Foundation (1–2 weeks)
- Set up FastF1 ingestion pipeline
- Design and build PostgreSQL schema
- Load and validate 2023/24 seasons
- Write a clean README documenting schema decisions
- **Milestone:** Working database you can query with SQL

### Phase 2 — ML + Visualisation (2–3 weeks)
- Telemetry feature engineering (per corner profiles)
- Driver clustering / style fingerprinting
- Tyre degradation modelling
- Deploy basic React dashboard showing Driver DNA visualisation
- Set up MLflow for experiment tracking
- **Milestone:** First shareable demo — visual, interactive, impressive

### Phase 3 — RAG + Chat (2–3 weeks)
- Set up pgvector extension
- Embed and index ML insights + race reports
- Build chat interface with streaming responses
- Implement query routing logic (SQL vs RAG)
- **Milestone:** Working chat that answers questions grounded in real data

### Phase 4 — Polish + Ship (1–2 weeks)
- UI polish (dark theme, F1-inspired design)
- Deploy to Vercel + Railway
- Write comprehensive README with architecture diagram
- Publish LinkedIn post about the build process
- **Milestone:** Live product with a real domain, ready to demo in interviews

**Total estimated timeline: 8–10 weeks**

---

## What Makes This Stand Out

- **Not a tutorial project** — no public walkthrough exists for this specific combination
- **Full stack depth** — covers data engineering, ML, RAG, vector DB, SQL, and React in one coherent system
- **Real domain expertise** — the pipeline to make answers accurate is the hard part, and the moat
- **Shippable product** — real users (F1 fans) can actually use it
- **Interview story** — every layer of the stack is a talking point with a clear "why" behind it

---

## Key Design Principle

> Start with 2023/24 seasons only. Make that slice excellent before expanding. Depth over breadth — a system that answers questions about two seasons *really well* is more impressive than one that handles all seasons poorly.

---

## Supporting Research (for README / pitch context)

These studies validate the broader "grounded AI" thesis:

- **MIT Media Lab (2025)** — "Your Brain on ChatGPT": students using ungrounded AI showed lower retention and cognitive engagement
- **Wharton School (2024)** — "Generative AI Can Harm Learning": AI without constraints promotes surface-level understanding
- **Macro Buddy Study (2026)** — Socratic, question-based AI outperformed answer-giving AI on exam scores

*Framing angle for README: This project is a demonstration that AI is most valuable when it's grounded in real, structured data — not when it's left to hallucinate.*

---

## Next Steps

1. Set up project repo on GitHub with a clear folder structure
2. Install FastF1 and start exploring the data in a Jupyter notebook
3. Design the PostgreSQL schema (lap times, stints, telemetry, circuits, drivers)
4. Build the ingestion pipeline for the 2024 season first
5. Return to this document and check off Phase 1 milestone
