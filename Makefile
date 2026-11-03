.PHONY: up down test build migrate
up:
	docker compose up --build -d
down:
	docker compose down
test:
	python -m pytest -q
build:
	npm --prefix frontend ci
	npm --prefix frontend run build
migrate:
	python seed_data.py
