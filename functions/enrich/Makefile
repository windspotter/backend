# Docker-free Lambda build (SAM BuildMethod: makefile). Target name = the
# function's logical ID in template.yaml. SAM sets $ARTIFACTS_DIR.
build-EnrichFunction:
	python3 -m pip install -r requirements.txt --platform manylinux2014_aarch64 --implementation cp --python-version 3.12 --only-binary=:all: --target "$(ARTIFACTS_DIR)"
	cp handler.py "$(ARTIFACTS_DIR)/"
	cp -r ../../spot_consultant "$(ARTIFACTS_DIR)/"
