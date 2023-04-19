IMAGE_NAME=letov
TAG=latest

build:
	docker build -t $(IMAGE_NAME):$(TAG) .
