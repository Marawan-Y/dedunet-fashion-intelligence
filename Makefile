.PHONY: setup run down test validate mutation contract bootstrap verify

SERVICE := services/commerce-api

setup:
	@test -f .env || cp .env.example .env

run: setup
	docker compose up --build

down:
	docker compose down

# PYTHONDONTWRITEBYTECODE and -p no:cacheprovider are deliberate, not decoration. Bytecode
# caches copied between checkouts have previously executed in the wrong tree, because
# Python validates a .pyc against source mtime and size, both preserved by a file copy.
test:
	cd $(SERVICE) && PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider

validate:
	python -B scripts/validation/validate_product_data.py
	python -B scripts/validation/validate_candidate_data.py

mutation:
	python -B scripts/validation/mutation_guard_check.py

contract:
	cd $(SERVICE) && python -B manage.py export-openapi

bootstrap:
	cd $(SERVICE) && python -B manage.py bootstrap

verify: test validate mutation contract
