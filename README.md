# Revolut Business — Fintech API, Security & GTM Portfolio

**Developer:** SkynetAI-Labs
**Project type:** Independent fintech engineering and commercial strategy case study
**Status:** Labs 1–2 implemented and tested; Labs 3–5 planned

> Independent educational simulation. Not affiliated with, endorsed by, or connected to Revolut. All customers, accounts and transactions are fictional.

## Project Overview

A five-lab portfolio combining fintech engineering, application security, DevSecOps, transaction monitoring and commercial strategy relevant to UK SMEs.

## Lab 1 — Business Banking API

Implemented:
- FastAPI application with interactive OpenAPI documentation
- SQLite database with fictional business customers and GBP accounts
- Customer, account balance and transaction history retrieval
- Internal payment service for simulated transfers
- Parameterised SQL and foreign-key enforcement
- Non-negative balance constraints
- Atomic transfers and transaction rollback
- Insufficient-funds and currency compatibility checks
- Rejection of invalid amounts, same-account transfers and nonexistent accounts
- Automated API and payment integrity tests

Payment execution is an internal Python service, with no public HTTP payment endpoint.

## Lab 2 — Authentication and API Security

Implemented:
- Signed JWT access tokens with required expiry and subject claims
- Token expiry and signature validation
- Database checks confirming authenticated users exist
- Administrator role checks
- Customer and account queries scoped to the authenticated customer
- Transaction queries restricted to transfers involving the customer's accounts
- Argon2id password hashing and password verification
- Internal registration and credential-authentication helpers
- Minimum 12-character registration passwords
- Standard user role assigned on registration
- IP-based request limits
- Security response headers

Headers:
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Referrer-Policy: no-referrer

Registration, credential authentication and token creation are internal Python helpers. Public registration and login HTTP endpoints are not implemented.

## API Endpoints

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| GET | `/` | Public | Project information |
| GET | `/health` | Public | Health check |
| GET | `/customers` | Bearer token | Authenticated customer's record |
| GET | `/accounts` | Bearer token | Authenticated customer's accounts |
| GET | `/transactions` | Bearer token | Transfers involving the customer's accounts |
| GET | `/admin/security-status` | Administrator bearer token | Demonstration administrator route |

Protected requests require an Authorization header containing Bearer followed by the access token.

## Technology Stack

Python, FastAPI, Pydantic, SQLite, PyJWT, python-dotenv, pwdlib with Argon2 support, SlowAPI, Pytest, HTTPX, Bandit, Gitleaks, Git and GitHub.

## Local Setup

Run commands from the repository root in an activated Python virtual environment.

Install dependencies:

    python -m pip install fastapi uvicorn pytest httpx email-validator PyJWT python-dotenv 'pwdlib[argon2]' slowapi bandit

Dependency versions are not yet locked in a committed manifest.

Configure a private local .env file with:
- JWT_SECRET_KEY: a securely generated signing secret
- JWT_ALGORITHM: HS256
- JWT_EXPIRE_MINUTES: 30

Never commit the signing secret or .env file. Preserve an existing .env when continuing this lab.

Initialise the database:

    python -m app.models

Fictional customers, accounts and users require separate setup.

Start locally:

    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

[Local API documentation](http://127.0.0.1:8000/docs) is available while the server runs.

## Automated Testing

Run:

    python -m pytest

**Latest verified result: 38 passed, 7 dependency deprecation warnings — 22 October 2026.**

Coverage includes:
- Public and authenticated banking routes
- Missing credentials and nonexistent users
- JWT creation, expiry and tampered signatures
- API rejection of missing-expiry, expired and tampered tokens
- Administrator access control
- Customer, account and transaction isolation
- Password hashing and verification
- Registration validation and duplicate rejection
- Rate limits and security headers
- Payment validation and transfer integrity

API, payment, user, role and tenant tests use temporary SQLite database fixtures.

## Security Verification

Verified before publishing implementation commit 758a3fb:

| Check | Result |
|---|---|
| Full test suite | 38 passed |
| Bandit application scan | No issues reported |
| Gitleaks staged scan | No leaks found |
| Git whitespace check | Passed |

Commands used:

    python -m bandit -r app/ -ll
    gitleaks protect --staged --redact
    git diff --cached --check

Gitleaks is installed separately. The command matches the version used in this lab. The staged scan does not establish that the entire repository history is free of secrets.

## Current Limitations

This is an educational prototype, not a production banking system.

- Public registration and login endpoints are not implemented.
- Payment execution remains an internal service.
- Token revocation, refresh-token flows and multi-factor authentication are not implemented.
- Rate limiting uses in-memory storage.
- Dependency locking and reproducible setup need further work.
- Containerisation and automated CI security checks are planned for Lab 3.
- Fraud monitoring and commercial research remain planned.

Passing tests and scans demonstrate the checks performed; they do not establish production readiness. Use fictional data only.

## Development Roadmap

| Lab | Focus | Status |
|---|---|---|
| 1 | Business Banking API | Implemented and tested |
| 2 | Authentication and API Security | Implemented and tested |
| 3 | Docker, GitHub Actions and DevSecOps | Planned |
| 4 | Fraud Detection and Transaction Monitoring | Planned |
| 5 | Revolut Business Market Intelligence and GTM | Planned |

## Project Disclaimer

Independent educational portfolio project developed by SkynetAI-Labs.

Not affiliated with or endorsed by Revolut. No real banking systems, customer data or funds are used.
