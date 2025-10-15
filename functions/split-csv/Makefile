# NOTE: This function is now deployed via Terraform (see terraform/cloud_functions/)
# This Makefile is kept for convenience commands only

# Configuration
PROJECT_ID ?= $(shell gcloud config get-value project)
REGION = europe-west2
FUNCTION_NAME = pydocs-split-csv

# View logs
.PHONY: logs
logs:
	gcloud functions logs read $(FUNCTION_NAME) \
		--region=$(REGION) \
		--project=$(PROJECT_ID) \
		--limit=50

# View function details
.PHONY: describe
describe:
	gcloud functions describe $(FUNCTION_NAME) \
		--region=$(REGION) \
		--project=$(PROJECT_ID) \
		--gen2