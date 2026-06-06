# QuantFlow Terminal

Production-grade institutional trading and research platform.

## Quick Start

```bash
# 1. Copy environment config
cp .env.example .env
# Edit .env with your API keys and passwords

# 2. Generate JWT keys
mkdir -p secrets
openssl genrsa -out secrets/private.pem 2048
openssl rsa -in secrets/private.pem -pubout -out secrets/public.pem

# 3. Start the stack
docker compose up -d

# 4. Run migrations
./scripts/migrate.sh up

# 5. Seed the database
docker compose exec backend python scripts/seed_symbols.py

# 6. Open the app
open http://localhost:3000
```

## Services

| Service      | URL                        |
|-------------|----------------------------|
| Frontend     | http://localhost:3000      |
| API          | http://localhost:8000      |
| API Docs     | http://localhost:8000/api/docs |
| Flower       | http://localhost:5555      |
| RabbitMQ UI  | http://localhost:15672     |

## Architecture

- **Backend**: FastAPI + asyncpg + SQLAlchemy 2.0
- **Database**: PostgreSQL 16 + TimescaleDB
- **Cache**: Redis 7
- **Queue**: RabbitMQ 3.13 + Celery 5
- **Frontend**: Next.js 14 (App Router) + TypeScript
- **Infra**: Docker Compose (dev) / Kubernetes (prod)

## Modules

1. Options Analytics Engine (BSM + Greeks)
2. Dealer Positioning (GEX/DEX/VEX/CEX)
3. Volatility Regime (HMM classifier)
4. PEAD Earnings Alpha
5. Flow Scanner
6. Risk Engine (VaR/ES)
7. Research Lab (backtesting)
8. Gold Analytics
9. Futures Flow
10. AI Research Assistant

## Testing

```bash
cd backend
pip install -e ".[dev]"
pytest tests/ -v
```
