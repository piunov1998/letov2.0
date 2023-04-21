IMAGE_NAME=letov
TAG=latest

build:
	docker build -t $(IMAGE_NAME):$(TAG) .

pull:
	git pull

update: pull build
	docker-compose up -d
