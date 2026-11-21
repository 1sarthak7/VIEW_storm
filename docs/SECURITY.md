# ViewStorm Security and Operator RBAC Architecture

This document outlines the security architecture, role-based access control (RBAC), cryptography standards, and operational guardrails implemented in ViewStorm.

---

## 1. Authentication & RBAC Model

ViewStorm enforces a multi-tier Operator Role-Based Access Control model:

| Role | Permissions | Use Case |
|---|---|---|
| **Admin** | Full system control: user provisioning, emergency halt/clear, simulation management, worker nodes | System administrators & infrastructure leads |
| **Operator** | Create, start, stop simulations; execute standardized benchmarks | Test engineers & performance specialists |
| **Viewer** | Read-only access to simulations, real-time analytics, reports, worker nodes | Stakeholders, monitoring dashboards, guests |

### Authentication Scheme
- **Mechanism**: JWT (JSON Web Tokens) with HMAC-SHA256 (`HS256`).
- **Token Format**: Standard Bearer token in the `Authorization` HTTP header:
  ```http
  Authorization: Bearer <access_token>
  ```
- **Session Duration**: Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` (defaults to 24 hours).

---

## 2. Password Hashing with Argon2id

Passwords are never stored in plaintext. ViewStorm utilizes state-of-the-art **Argon2id** password hashing adhering to OWASP recommendations:

```python
pwd_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=19456,  # 19 MiB
    parallelism=1,
    hash_len=32,
    salt_len=16,
)
```

- **Algorithm**: Argon2id (hybrid data-dependent and data-independent memory access resistant to both side-channel attacks and GPU brute-force).
- **Verification**: Constant-time verification through `pwd_hasher.verify`.

---

## 3. Brute-Force Rate Limiting

To mitigate credential stuffing and brute-force password guessing attacks:
- Failed login attempts are tracked per username in Redis: `viewstorm:auth:rate_limit:<username>`.
- Threshold: 5 failed attempts within a 5-minute rolling window (`LOGIN_RATE_LIMIT_MAX_ATTEMPTS=5`, `LOGIN_RATE_LIMIT_WINDOW_SECONDS=300`).
- Exceeding the threshold triggers an immediate `HTTP 429 Too Many Requests` locking the account for the duration of the window.
- Successful login automatically resets the failure counter.

---

## 4. Target Environment Guardrails

ViewStorm is strictly an authorized testing and simulation system. It contains hardcoded safety constraints preventing unauthorized denial-of-service traffic:
- Permitted target environments are strictly validated against `ALLOWED_TARGET_ENVIRONMENTS` (`local`, `test`, `staging-authorized`).
- Target URLs are validated against local/internal addresses:
  - `http://127.0.0.1:8000`
  - `http://localhost:8000`
  - `http://backend:8000`
- Any attempt to target external social media platforms or unauthorized external endpoints immediately aborts with `HTTP 403 Forbidden` (`UnauthorizedTargetError`).
