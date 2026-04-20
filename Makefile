# ============================================================
# EU Economic Monitor - Makefile
# ============================================================

.PHONY: help setup terraform-init terraform-plan terraform-apply terraform-check \
        up down logs ingest spark-batch flink-streaming dbt-run pipeline \
        open-dashboard open-console open-flink build build-clean clean create-topics

DOCKER_COMPOSE = docker compose
ENV_FILE       = .env

help:            ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# -----------------------------------------------------------
# Setup
# -----------------------------------------------------------
setup:           ## Copy .env.example → .env (first-time setup)
	@if [ ! -f $(ENV_FILE) ]; then \
	  cp .env.example $(ENV_FILE); \
	  echo ".env created - fill in your GCP values before proceeding."; \
	else \
	  echo ".env already exists."; \
	fi
	@mkdir -p credentials
	@echo "Place your GCP service account JSON at: credentials/service-account.json"

# -----------------------------------------------------------
# Terraform (GCP Infrastructure)
# -----------------------------------------------------------
terraform-init:  ## Initialise Terraform providers
	cd terraform && terraform init

terraform-plan:  ## Preview Terraform changes
	cd terraform && terraform plan -var-file=terraform.tfvars

terraform-apply: ## Apply Terraform - provisions GCP resources
	cd terraform && terraform apply -var-file=terraform.tfvars -auto-approve

terraform-destroy: ## Destroy all GCP resources (irreversible!)
	cd terraform && terraform destroy -var-file=terraform.tfvars

terraform-check: ## Verify GCP infrastructure is provisioned (plan; fails if not initialised)
	@echo "Checking Terraform state..."
	@if [ ! -f terraform/terraform.tfstate ] || [ ! -s terraform/terraform.tfstate ]; then \
	  echo "No tfstate found - running terraform apply to provision GCP infrastructure..."; \
	  cd terraform && terraform init -input=false && terraform apply -var-file=terraform.tfvars -auto-approve; \
	else \
	  echo "tfstate found. Running plan to detect drift..."; \
	  cd terraform && terraform plan -var-file=terraform.tfvars -detailed-exitcode 2>&1 | tail -5; \
	fi

# -----------------------------------------------------------
# Docker - Core Services (Redpanda + Dashboard)
# -----------------------------------------------------------
up:              ## Start long-running services (Redpanda, Flink cluster, Consumer, Dashboard)
	$(DOCKER_COMPOSE) up -d redpanda redpanda-console redpanda-consumer flink-jobmanager flink-taskmanager dashboard
	@echo "Services started. Dashboard: http://localhost:8501"
	@echo "Redpanda Console: http://localhost:8080"
	@echo "Flink Web UI:     http://localhost:8081"
	@echo "Run 'make flink-streaming' to submit the streaming job."

down:            ## Stop all services
	$(DOCKER_COMPOSE) down

logs:            ## Tail logs from all services
	$(DOCKER_COMPOSE) logs -f

# -----------------------------------------------------------
# Redpanda Topic Creation
# -----------------------------------------------------------
create-topics:   ## Create Redpanda topics (idempotent)
	-$(DOCKER_COMPOSE) exec redpanda rpk topic create eurostat.ingestion.completed --partitions 3 --replicas 1
	-$(DOCKER_COMPOSE) exec redpanda rpk topic create eurostat.anomalies --partitions 3 --replicas 1
	@echo "Topics ready."

# -----------------------------------------------------------
# Pipeline - Run in order
# -----------------------------------------------------------
ingest:          ## Run dlt ingestion pipeline (pulls Eurostat → BigQuery)
	$(DOCKER_COMPOSE) --profile pipeline run --rm dlt-ingestion

spark-batch:     ## Run Spark batch job (process raw → processed BigQuery tables)
	$(DOCKER_COMPOSE) --profile pipeline run --rm spark-batch

flink-streaming: ## Submit PyFlink streaming job to the running Flink cluster
	$(DOCKER_COMPOSE) exec flink-jobmanager flink run \
		-py /opt/flink/usrlib/streaming_job.py \
		--pyFiles /opt/flink/usrlib/
	@echo "Streaming job submitted. Monitor at http://localhost:8081"

dbt-run:         ## Run dbt transformations (staging → intermediate → marts)
	$(DOCKER_COMPOSE) --profile pipeline run --rm dbt

pipeline:        ## Full pipeline: ingest → spark → dbt
	@echo " Step 1/3 - dlt Ingestion..."
	$(MAKE) ingest
	@echo " Step 2/3 - Spark Batch Processing..."
	$(MAKE) spark-batch
	@echo " Step 3/3 - dbt Transformations..."
	$(MAKE) dbt-run
	@echo " Pipeline complete! Open http://localhost:8501"

# -----------------------------------------------------------
# Convenience
# -----------------------------------------------------------
open-dashboard:  ## Open Streamlit dashboard in default browser
	start http://localhost:8501

open-console:    ## Open Redpanda Console in default browser
	start http://localhost:8080

open-flink:      ## Open Flink Web UI in default browser
	start http://localhost:8081

build:           ## Build Docker images (uses layer cache - fast on re-runs)
	$(DOCKER_COMPOSE) build

build-clean:     ## Force-rebuild all images from scratch (no cache)
	$(DOCKER_COMPOSE) build --no-cache

clean:           ## Remove stopped containers and unused images
	$(DOCKER_COMPOSE) down --remove-orphans
	docker image prune -f