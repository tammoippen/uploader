dev:
	poetry run uvicorn uploader:app --reload

docker:
	docker run -it --rm --name uploader -p 127.0.0.1:8000:80 \
			-e UPLDR_JWT_SECRET \
			-e UPLDR_ADMIN_SECRET \
			-e UPLDR_LOCAL_PATH \
			-e UPLDR_GCS_PATH \
			-v ${PWD}:/app \
			-e PORT=8000 \
			tammoippen/uploader:latest --reload

build:
	docker build -t tammoippen/uploader:latest .

format:
	poetry run black .

static:
	poetry run flake8
	poetry run black --check .
