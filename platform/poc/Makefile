.PHONY: setup run test validate down

setup:
	@test -f .env || cp .env.example .env

run: setup
	docker compose up --build

test:
	cd backend && pytest -q

validate:
	python scripts/validate_product_data.py

down:
	docker compose down
