# Revolut Business — Fintech API, Security & GTM Portfolio

**Developer:** SkynetAI-Labs
**Project type:** Independent fintech engineering and commercial strategy case study
**Status:** Labs 1–3 implemented and tested; Lab 3 documentation and closeout in progress; Labs 4–5 planned

> Independent educational simulation. Not affiliated with, endorsed by, or connected to Revolut. All customers, accounts and transactions are fictional.

## Project Overview

A five-lab portfolio combining fintech engineering, application security, DevSecOps, transaction monitoring and commercial strategy relevant to UK SMEs.

Portfolio Labs 8 and 9 represent the API-development and authentication phases of this repository. They correspond to internal project Labs 1 and 2 below.

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

The initial API milestone passed 11 tests. The expanded combined project suite now contains 38 passing tests.

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

Implemented roles are `admin` and `user`.

Security headers:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`

Registration, credential authentication and token creation are internal Python helpers. Public registration and login HTTP endpoints are not implemented.

## Lab 3 — Docker, GitHub Actions and DevSecOps

Implemented:

- Separate runtime and development dependency manifests
- Exact version pins for declared direct dependencies
- Test JWT configuration using a fresh generated secret per pytest process
- Fresh-environment installation and test verification
- Successful tests from a temporary project copy without the local `.env` or banking database
- Docker image using Python 3.14.9 and Alpine Linux
- Base image pinned by SHA-256 digest
- Binary-wheel-only runtime dependency installation and dependency consistency check
- Removal of pip and ensurepip after runtime dependency installation
- Non-root application execution as UID/GID 10001
- Docker build-context exclusions for secrets, local databases, virtual environments, caches and development files
- GitHub Actions testing and automated security checks

The workflow runs on pushes to `main`, pull requests targeting `main` and manual dispatch. It uses read-only repository-content permissions and disables persisted checkout credentials.

Workflow checks:

1. Install dependencies and check consistency
2. Run the complete test suite
3. Scan application source with Bandit
4. Audit installed Python packages with pip-audit
5. Scan checked-out repository files with Gitleaks
6. Build and export the application image
7. Scan the image with Trivy

The image is built for verification; the workflow does not publish it.

### Vulnerability Remediation

The first GitHub run failed the container security gate. The original Debian image reported 101 HIGH and 3 CRITICAL package findings.

A newer Debian candidate reduced the findings but still failed. An alternative Bookworm base also failed evaluation.

The selected Alpine base reported no HIGH/CRITICAL operating-system findings. Four remaining HIGH Python findings were traced to libraries bundled inside pip. The runtime image now excludes installed pip and its ensurepip installation archive after dependencies are installed.

The completed Alpine candidate reported zero HIGH/CRITICAL findings across the scanned operating-system and Python packages. No ignore exceptions or reduced failure thresholds were introduced.

**GitHub Actions run for fix commit `d2ff68f`: passed, verified on 22 October 2026.**

## API Endpoints

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| GET | `/` | Public | Project information |
| GET | `/health` | Public | Health check |
| GET | `/customers` | Bearer token | Authenticated customer's record |
| GET | `/accounts` | Bearer token | Authenticated customer's accounts |
| GET | `/transactions` | Bearer token | Transfers involving the customer's accounts |
| GET | `/admin/security-status` | Administrator bearer token | Demonstration administrator route |

Protected requests require an `Authorization: Bearer <token>` header.

Rate limits per remote address:

| Routes | Limit |
|---|---|
| `/`, `/health` | 60/minute each |
| `/customers`, `/accounts` | 30/minute each |
| `/transactions` | 20/minute |
| `/admin/security-status` | 10/minute |

## Technology Stack

Python, FastAPI, Pydantic, SQLite, PyJWT, python-dotenv, pwdlib with Argon2 support, SlowAPI, Uvicorn, pytest, HTTPX, Docker, Alpine Linux, GitHub Actions, Bandit, pip-audit, Gitleaks and Trivy.

CI and the selected container use Python 3.14.9. The original Ubuntu virtual environment used Python 3.14.4.

## Local Setup

Run commands from the repository root in a Python virtual environment.

Install runtime dependencies:

    python -m pip install -r requirements.txt

For tests and development security tools:

    python -m pip install -r requirements-dev.txt
    python -m pip check

The manifests pin direct dependencies. Transitive dependencies are not fully locked or hash-pinned.

Configure a private local `.env` file with:

- `JWT_SECRET_KEY`: a securely generated signing secret
- `JWT_ALGORITHM`: `HS256`
- `JWT_EXPIRE_MINUTES`: `30`

Never commit the signing secret or `.env` file. Preserve an existing `.env` when continuing the project.

Initialise the database:

    python -m app.models

Fictional customers, accounts and users require separate setup.

Start locally:

    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

API documentation while the server runs:

http://127.0.0.1:8000/docs

## Container Usage

Build the image:

    docker build -t revolut-fintech-api:local .

In the verified Ubuntu/WSL environment, Docker inherited a DNS resolver that failed inside its default network. The local build used this workaround:

    docker build --network=host -t revolut-fintech-api:local .

The GitHub workflow passed with the standard build command. The local workaround does not change the application's runtime networking.

Start the container using local configuration:

    docker run -d --name revolut-fintech-api --env-file .env -p 127.0.0.1:8000:8000 revolut-fintech-api:local

The image excludes `.env` and the local banking database. Configuration is supplied at runtime.

For a new container, initialise an empty database schema separately:

    docker exec revolut-fintech-api python -m app.models

This does not seed customers, accounts or users. The health route does not check database readiness. Authenticated banking operations require suitable fictional database records.

Database changes remain in the container's writable layer unless persistence is configured. Removing that container loses those changes.

The final runtime image intentionally has no pip or ensurepip. Change dependencies through the manifests and rebuild the image.

Verified container behaviour:

- `/health`: 200 with the expected response
- `/accounts` without credentials: 401 with `WWW-Authenticate: Bearer`
- All three security headers present
- UID/GID 10001
- Graceful container shutdown

## Automated Testing

Run:

    python -m pytest tests -q

`tests/conftest.py` supplies test JWT settings before application imports. Database-dependent tests use temporary SQLite fixtures.

**Latest verified local result: 38 passed, 7 dependency deprecation warnings — 22 October 2026.**

This result was verified in a fresh Ubuntu environment, an isolated project copy and an Alpine Python 3.14.9 compatibility container.

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

The warnings concern Starlette's HTTPX TestClient integration and SlowAPI's deprecated asyncio API usage. They remain unresolved.

## Security Verification

| Check | Verified result or enforced policy |
|---|---|
| Full test suite | 38 passing tests locally; GitHub test step passed |
| Dependency consistency | Passed |
| Bandit | GitHub scan passed; reported findings fail the job |
| pip-audit | GitHub audit passed; reported vulnerabilities fail the job |
| Gitleaks | GitHub file scan passed; staged scans reported no leaks |
| Trivy | Completed candidate reported zero HIGH/CRITICAL findings; GitHub scan passed |
| Git whitespace checks | Passed before publication |

Workflow versions include Gitleaks 8.30.1 and Trivy 0.76.1.

Trivy fails on HIGH/CRITICAL vulnerabilities, including unfixed findings. No explicit vulnerability exceptions were added. Results reflect the vulnerability database available at scan time.

Trivy also emitted a third-party SBOM accuracy warning. A passing scan does not guarantee that every vulnerability or component was detected.

Local commands used:

    python -m bandit -r app
    python -m pip_audit
    gitleaks protect --staged --redact
    git diff --cached --check

The local staged Gitleaks command matches the separately installed version used in this lab. The GitHub workflow uses the newer containerised CLI.

Neither staged scanning nor the workflow's checked-out-file scan establishes that the entire Git history is free of secrets.

## Current Limitations

This is an educational prototype, not a production banking system.

- Public registration and login endpoints are not implemented.
- Payment execution remains an internal service.
- Token revocation, refresh-token flows and multi-factor authentication are not implemented.
- Rate limiting uses remote-address keys and in-memory storage.
- Direct dependency pins do not provide a complete transitive lockfile.
- Container database initialisation, fictional data seeding and persistence require explicit setup.
- Container smoke checks covered health and unauthenticated rejection; authenticated behaviour was covered by automated tests.
- The local Docker DNS workaround and legacy-builder deprecation notice remain environment considerations.
- Dependency deprecation warnings remain unresolved.
- Security steps run sequentially, so a failure can prevent later checks from running.
- Fraud monitoring and commercial research remain planned.

Passing tests and scans demonstrate the checks performed; they do not establish production readiness. Use fictional data only.

## Development Roadmap

| Lab | Focus | Status |
|---|---|---|
| 1 | Business Banking API | Implemented and tested |
| 2 | Authentication and API Security | Implemented and tested |
| 3 | Docker, GitHub Actions and DevSecOps | Implemented; GitHub checks passed; documentation and closeout in progress |
| 4 | Fraud Detection and Transaction Monitoring | Planned |
| 5 | Revolut Business Market Intelligence and GTM | Planned |

## Project Disclaimer

Independent educational portfolio project developed by SkynetAI-Labs.

Not affiliated with or endorsed by Revolut. No real banking systems, customer data or funds are used.
