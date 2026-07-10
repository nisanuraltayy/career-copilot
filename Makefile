# Sık kullanılan komutlar için kısayollar.
# Windows'ta `make` yoksa komutları doğrudan çalıştırabilirsiniz (README'ye bakın).

.PHONY: install dev test lint fmt cov run migrate up down

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements-dev.txt

test:
	pytest

cov:
	pytest --cov

lint:
	ruff check app tests alembic

fmt:
	ruff check --fix app tests alembic

run:
	uvicorn app.main:app --reload

migrate:
	alembic upgrade head

up:
	docker compose up --build -d

down:
	docker compose down
