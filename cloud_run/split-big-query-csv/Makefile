# Configuration
PROJECT_ID ?= $(shell gcloud config get-value project)
REGION = europe-west2
SOURCE_BUCKET = pydocs-bq
FUNCTION_NAME = pydocs-split-csv
ENTRY_POINT = split_csv_file
RUNTIME = python312
TRIGGER_EVENT_TYPE = google.cloud.storage.object.v1.finalized

# Deploy the Cloud Function with EventArc trigger
.PHONY: deploy
deploy:
	gcloud functions deploy $(FUNCTION_NAME) \
		--gen2 \
		--runtime=$(RUNTIME) \
		--region=$(REGION) \
		--source=. \
		--entry-point=$(ENTRY_POINT) \
		--trigger-event-filters="type=$(TRIGGER_EVENT_TYPE)" \
		--trigger-event-filters="bucket=$(SOURCE_BUCKET)" \
		--trigger-location=$(REGION) \
		--memory=512Mi \
		--timeout=540s \
		--max-instances=10 \
		--project=$(PROJECT_ID)

# Delete the function
.PHONY: delete
delete:
	gcloud functions delete $(FUNCTION_NAME) \
		--region=$(REGION) \
		--project=$(PROJECT_ID) \
		--quiet

# View logs
.PHONY: logs
logs:
	gcloud functions logs read $(FUNCTION_NAME) \
		--region=$(REGION) \
		--project=$(PROJECT_ID) \
		--limit=50