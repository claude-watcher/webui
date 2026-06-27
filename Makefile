.PHONY: install run dev lint test docker-build docker-run clean

install:
	uv sync

run:
	uv run python main.py

dev:
	APP_RELOAD=true uv run python main.py

lint:
	pre-commit run --all-files

test:
	uv run pytest

docker-build:
	docker build -t claude-watcher-webui:local .

docker-run:
	docker run --rm --pid=host -u $$(id -u):$$(id -g) -e HOME=$$HOME \
		-v $$HOME:$$HOME:ro \
		-p 8000:8000 \
		claude-watcher-webui:local

clean:
	rm -rf __pycache__ .mypy_cache .pytest_cache .ruff_cache .coverage htmlcov
