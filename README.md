# QuantFlow Terminal

<p align="center">
  <img src="img/Capture d'écran 2026-06-04 230639.png" alt="QuantFlow diagram" width="900" />
</p>

> Production-grade institutional trading & research platform — implementation specification.

## Overview

- Backend: FastAPI, PostgreSQL 16 + TimescaleDB, Redis, RabbitMQ
- Frontend: Next.js (App Router), TypeScript, Tailwind
- Core: Options analytics (BSM pricer), Dealer positioning (GEX/DEX), Volatility regimes, PEAD research
- Infra: Docker Compose for development, Kubernetes + Helm for production

## Contents

This repo contains a full implementation specification for QuantFlow Terminal including:

- Folder structure and module breakdown
- Database DDL for core tables (options, greeks, flow_events, dealer_positioning)
- API architecture and complete endpoint list (FastAPI)
- Core algorithms: BSM pricer, volatility surface, dealer positioning engine
- Data pipeline schedule (Celery beat) and market data sources
- Infrastructure (Docker Compose, Kubernetes HPA)
- Security, testing strategy, and development roadmap

For the complete specification, see the original spec: [Quantflow terminal spec.md](Quant%20Flow/Quantflow%20terminal%20spec.md)

## Quickstart (development)

1. Start the dev stack:

```powershell
docker-compose up --build
```

2. Backend API available at `http://localhost:8000`
3. Frontend available at `http://localhost:3000`

## Image

The diagrams below are taken from the `img/` folder — they illustrate the platform UI and architecture.

### Screenshots

<p align="center">
  <img src="img/Capture d'écran 2026-06-04 230804.png" alt="Dealer map" width="700" />
</p>

<p align="center">
  <img src="img/Capture d'écran 2026-06-04 230812.png" alt="Options chain" width="700" />
</p>

<p align="center">
  <img src="img/Capture d'écran 2026-06-04 230822.png" alt="Overview" width="700" />
</p>

<p align="center">
  <img src="img\Capture d'écran 2026-06-04 230830.png" alt="Overview" width="700" />
</p>

<p align="center">
  <img src="img\Capture d'écran 2026-06-04 230837.png" alt="Overview" width="700" />
</p>

<p align="center">
  <img src="img\Capture d'écran 2026-06-04 230844.png" alt="Overview" width="700" />
</p>

<p align="center">
  <img src="img\Capture d'écran 2026-06-04 230851.png" alt="Overview" width="700" />
</p>

<p align="center">
  <img src="img\Capture d'écran 2026-06-04 230858.png" alt="Overview" width="700" />
</p>

<p align="center">
  <img src="img\Capture d'écran 2026-06-04 230905.png" alt="Overview" width="700" />
</p>

<p align="center">
  <img src="img\Capture d'écran 2026-06-04 230912.png" alt="Overview" width="700" />
</p>



If you'd like different screenshots or captions, tell me which ones to use and I will update them.

## Project layout (high-level)

```
quantflow/
├── backend/        # FastAPI app, services, models, schemas, tasks
├── frontend/       # Next.js app (TypeScript, Tailwind)
├── infra/          # Docker, k8s, helm charts
├── scripts/        # Utility scripts (seed, backfill, migrate)
└── docs/           # Architecture docs and runbooks
```

## Where the content lives

- `backend/`: API and business logic (see `app/` inside `backend`)
- `frontend/`: UI components, hooks, and pages
- `infra/`: `docker-compose.yml`, Dockerfiles, Kubernetes manifests
- `scripts/`: helper scripts for seeding and migrations
- `Quantflow terminal spec.md`: detailed implementation specification (source of README content)

---

Generated from the project spec (`Quantflow terminal spec.md`).
