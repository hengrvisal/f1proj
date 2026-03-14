.PHONY: db-up db-down migrate ingest ingest-no-telemetry test api ml frontend

db-up:
	docker compose up -d

db-down:
	docker compose down

migrate:
	alembic upgrade head

ingest:
	python -m backend.ingestion.run_pipeline --year 2023 --year 2024

ingest-no-telemetry:
	python -m backend.ingestion.run_pipeline --year 2023 --year 2024 --skip-telemetry

test:
	pytest tests/ -v

api:
	uvicorn backend.api.main:app --reload

ml:
	python -m backend.ml.run_features --all

frontend:
	cd frontend && npm run dev
