IMAGE := ghcr.io/yevhenyaremenko/abox-labs-mcp-server
TAG   ?= latest

.PHONY: build push login

login:
	echo "$${CR_PAT}" | docker login ghcr.io -u yevhenyaremenko --password-stdin

build:
	docker build -t $(IMAGE):$(TAG) .

push:
	docker push $(IMAGE):$(TAG)
