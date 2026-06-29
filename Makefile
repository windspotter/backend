# SAM builds each function from a COPY of its CodeUri, so the recipe can only see
# files under CodeUri. We set the enrich function's CodeUri to the repo root (see
# infra/template.yaml) so the shared `spot_consultant` package is in the build copy.
# Paths below are relative to the repo root; the recipe assembles the Lambda zip in
# $ARTIFACTS_DIR (deps + handler + shared package).
build-EnrichFunction:
	python3 -m pip install -r functions/enrich/requirements.txt --platform manylinux2014_aarch64 --implementation cp --python-version 3.12 --only-binary=:all: --target "$(ARTIFACTS_DIR)"
	cp functions/enrich/handler.py "$(ARTIFACTS_DIR)/"
	cp -r spot_consultant "$(ARTIFACTS_DIR)/"
