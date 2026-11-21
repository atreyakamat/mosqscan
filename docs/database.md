# Vectora AI — Database Schema & Migration Specification

## 1. Overview

Vectora AI uses PostgreSQL in production and SQLite for local development and unit tests. Schema state is managed exclusively through Alembic migrations.

---

## 2. Relational Schema Architecture

```
       +--------------------+
       |       users        |
       +--------------------+
       | id (UUID, PK)      |
       | email (Unique)     |
       | username (Unique)  |
       | hashed_password    |
       | role (user/admin)  |
       | is_active          |
       | created_at         |
       +---------+----------+
                 |
      +----------+-----------------------+
      | 1:N                              | 1:N
+-----+--------------+       +-----------+----------+
|   refresh_tokens   |       |     submissions      |
+--------------------+       +----------------------+
| id (UUID, PK)      |       | id (UUID, PK)        |
| user_id (FK)       |       | user_id (FK)         |
| token_hash (SHA256)|       | type (adult/larvae)  |
| expires_at         |       | status (pending/...) |
| revoked            |       | created_at           |
+--------------------+       +---+-------+------+---+
                                 |       |      |
             +-------------------+       |      +--------------------+
             | 1:N                       | 1:1                       | 1:1
+------------+-------+       +-----------+----------+       +--------+---------+
|    media_files     |       |identification_results|       | processing_jobs  |
+--------------------+       +----------------------+       +------------------+
| id (UUID, PK)      |       | id (UUID, PK)        |       | id (UUID, PK)    |
| submission_id (FK) |       | submission_id (FK)   |       | submission_id(FK)|
| original_filename  |       | predicted_genus      |       | status           |
| stored_filename    |       | confidence           |       | frame_count      |
| file_path          |       | is_uncertain         |       | valid_frames     |
| sha256_checksum    |       | uncertainty_message  |       | started_at       |
| mime_type          |       | all_scores (JSON)    |       | completed_at     |
| file_size          |       | model_version        |       | error_message    |
+--------------------+       +----------------------+       +------------------+
```

---

## 3. Migration Workflow

Migrations are located in `backend/alembic/versions/`.
To apply migrations:

```bash
cd backend
alembic upgrade head
```

To create a new migration:

```bash
cd backend
alembic revision --autogenerate -m "Descriptive message"
```
