dev:
	uvicorn uploader:app --reload

docker:
	docker run -it --rm --name uploader -p 127.0.0.1:8000:80 \
			-e UPLDR_JWT_SECRET \
			-e UPLDR_ADMIN_SECRET \
			-e UPLDR_LOCAL_PATH \
			-e UPLDR_GCS_PATH \
			-e LOGURU_LEVEL=INFO \
			-e LOGURU_DIAGNOSE=False \
			-v $PWD:/app \
			uploader:latest --reload

format:
	black .

static:
	flake8
	black --check .
