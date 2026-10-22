# Revolut Business — Fintech API, Security & GTM Portfolio

**Developer:** SkynetAI-Labs  
**Project type:** Independent fintech engineering and commercial strategy case study  
**Status:** Lab 1 implementation complete; further labs planned

> Independent educational simulation inspired by fintech business banking. This project is not affiliated with, endorsed by, or connected to Revolut. No real banking systems or customer funds are used.

## Project Overview

A multi-stage portfolio project exploring the engineering, security, transaction monitoring, DevSecOps and go-to-market considerations of a modern business banking platform.

The project combines practical software engineering with commercial research relevant to UK SMEs and fintech business development.

## Lab 1 — Business Banking API

### Implemented Features

- Python FastAPI application
- Interactive OpenAPI documentation
- SQLite relational database
- Fictional business customers and GBP accounts
- Account balance retrieval
- Simulated internal account transfers
- Transaction history retrieval
- Database foreign-key constraints
- Non-negative account balance constraints
- Atomic transfers using SQLite transactions
- Insufficient-funds validation
- Rejection of zero and negative transfer amounts
- Rejection of same-account transfers
- Rejection of transfers involving nonexistent accounts
- Automated API and payment integrity tests

### API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Project information |
| GET | `/health` | Application health |
| GET | `/customers` | List fictional customers |
| GET | `/accounts` | List fictional accounts and balances |
| GET | `/transactions` | Retrieve simulated transaction history |

Payment execution is currently implemented as an internal Python service function, not as a public HTTP payment endpoint.

### Technology Stack

- Python
- FastAPI
- Pydantic
- SQLite
- Pytest
- HTTPX / FastAPI TestClient
- Git and GitHub

### Project Structure

```text
app/
  __init__.py
  main.py
  database.py
  models.py
  payments.py
  schemas.py
  data/                 # Local database; excluded from Git

tests/
  test_api.py
  test_payments.py
```

## Local Setup

Install dependencies:

    python -m pip install fastapi uvicorn pytest httpx email-validator

Initialise database:

    python -m app.models

Start API:

    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

API documentation: http://127.0.0.1:8000/docs

Demo accounts require separate setup.

## Automated Testing

Run all tests:

    python -m pytest tests/ -v

Latest verified result: 11 passed, 0 failed.

Coverage includes:
- Five API endpoint tests
- Five invalid-transfer tests
- One successful-transfer integrity test

Payment tests use isolated temporary SQLite databases.

## Security and Financial Integrity

Implemented safeguards:
- Parameterised SQL queries
- SQLite foreign-key enforcement
- Non-negative balance constraints
- Atomic transfers and transaction rollback
- Insufficient-funds validation
- Rejection of invalid transfer amounts
- Same-account transfer prevention
- Currency compatibility checks

## Current Security Limitations

This is an educational prototype, not a production banking system.

Authentication, authorisation, account ownership checks, rate limiting and production security controls are planned for Lab 2.

Current API listing endpoints have no access controls and must not be exposed with real customer data.

## Development Roadmap

- Lab 1: Business Banking API — Implementation and tests complete
- Lab 2: Authentication and API Security — Planned
- Lab 3: Docker, GitHub Actions and DevSecOps — Planned
- Lab 4: Fraud Detection and Transaction Monitoring — Planned
- Lab 5: Revolut Business Market Intelligence and GTM — Planned

## Project Disclaimer

Independent educational portfolio project developed by SkynetAI-Labs.

Not affiliated with or endorsed by Revolut. All customers, accounts and transactions are fictional.
