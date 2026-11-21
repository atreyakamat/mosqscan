# Vectora AI — Docker Deployment Guide

## 1. Prerequisites

- Docker 24.0+
- Docker Compose 2.20+
- Host CPU with AVX support (Intel Core i7-2600 / AMD equivalent, 16 GB RAM)
- No GPU / CUDA required (all models run via ONNX CPU execution provider)

---

## 2. Compose Architecture

The `docker-compose.yml` configures 5 isolated services:

1. **`postgres`**: Relational store for users, submissions, and audit trail.
2. **`redis`**: Message broker for asynchronous video processing jobs.
3. **`backend`**: FastAPI REST API handling authentication, uploads, and ONNX inference.
4. **`video_worker`**: Celery video processor analyzing larvae locomotion using OpenCV.
5. **`web`**: Next.js responsive web frontend (port 3000).

Internal services (`postgres`, `redis`) have no host port bindings and communicate over the private `vectora_net` bridge network.

---

## 3. Quick Start

```bash
# 1. Clone repository & configure environment
cp .env.example .env

# 2. Build and start containers
docker compose up -d --build

# 3. View status & health
docker compose ps
```

Services will be available at:
- Web Application: `http://localhost:3000`
- API & Swagger Docs: `http://localhost:8000/docs`
- Healthcheck: `http://localhost:8000/health`
