@echo off
setlocal EnableDelayedExpansion
title EU Economic Monitor - Full Pipeline Runner

:: ============================================================
:: Resolve script directory so the batch file can be double-
:: clicked from anywhere and still find the project root.
:: ============================================================
cd /d "%~dp0"

:: ============================================================
:: Colour helpers (Windows 10+)
:: ============================================================
set "RED=[91m"
set "GRN=[92m"
set "YLW=[93m"
set "CYN=[96m"
set "RST=[0m"

echo.
echo %CYN%============================================================%RST%
echo %CYN%  EU Economic Monitor - One-Click Pipeline Runner%RST%
echo %CYN%  Runs: build ^> up ^> topics ^> ingest ^> spark ^> dbt ^> dashboard%RST%
echo %CYN%============================================================%RST%
echo.

:: ============================================================
:: PRE-FLIGHT CHECKS
:: ============================================================
echo %YLW%[CHECK] Verifying prerequisites...%RST%

:: -- Docker --
docker info >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL] Docker is not running. Start Docker Desktop and try again.%RST%
    pause
    exit /b 1
)
echo %GRN%  [OK] Docker is running%RST%

:: -- Docker Compose v2 --
docker compose version >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL] Docker Compose v2 not found. Update Docker Desktop.%RST%
    pause
    exit /b 1
)
echo %GRN%  [OK] Docker Compose v2 available%RST%

:: -- Terraform --
terraform version >nul 2>&1
if errorlevel 1 (
    echo %YLW%  [WARN] Terraform not found - skipping GCP provisioning step.%RST%
    set SKIP_TERRAFORM=1
) else (
    echo %GRN%  [OK] Terraform available%RST%
    set SKIP_TERRAFORM=0
)

:: -- .env file --
if not exist ".env" (
    if exist ".env.example" (
        echo %YLW%  [WARN] .env not found - copying from .env.example%RST%
        copy ".env.example" ".env" >nul
        echo %YLW%  [ACTION REQUIRED] Edit .env and fill in GCP_PROJECT_ID and GCS_BUCKET_NAME,%RST%
        echo %YLW%  then re-run this script.%RST%
        pause
        exit /b 1
    ) else (
        echo %RED%[FAIL] .env and .env.example both missing. Cannot continue.%RST%
        pause
        exit /b 1
    )
)
echo %GRN%  [OK] .env exists%RST%

:: -- credentials/service-account.json --
if not exist "credentials\service-account.json" (
    echo %RED%[FAIL] credentials\service-account.json not found.%RST%
    echo %RED%       Follow Step 4 in README.md to create and download the bootstrap SA key.%RST%
    pause
    exit /b 1
)
echo %GRN%  [OK] credentials\service-account.json found%RST%

:: -- terraform\terraform.tfvars --
if "%SKIP_TERRAFORM%"=="0" (
    if not exist "terraform\terraform.tfvars" (
        if exist "terraform\terraform.tfvars.example" (
            echo %YLW%  [WARN] terraform.tfvars not found - copying from example%RST%
            copy "terraform\terraform.tfvars.example" "terraform\terraform.tfvars" >nul
            echo %YLW%  [ACTION REQUIRED] Edit terraform\terraform.tfvars with your project_id%RST%
            echo %YLW%  and gcs_bucket_name, then re-run this script.%RST%
            pause
            exit /b 1
        )
    )
    echo %GRN%  [OK] terraform.tfvars exists%RST%
)

echo.
echo %GRN%All pre-flight checks passed.%RST%
echo.

:: ============================================================
:: STEP 1 — TERRAFORM (optional, skip if not available)
:: ============================================================
if "%SKIP_TERRAFORM%"=="0" (
    echo %CYN%[1/7] Provisioning GCP infrastructure with Terraform...%RST%
    cd terraform
    terraform init -input=false
    if errorlevel 1 ( echo %RED%Terraform init failed.%RST% & cd .. & pause & exit /b 1 )
    terraform apply -var-file=terraform.tfvars -auto-approve
    if errorlevel 1 ( echo %RED%Terraform apply failed.%RST% & cd .. & pause & exit /b 1 )
    cd ..
    echo %GRN%  [OK] GCP infrastructure ready%RST%
    echo.
) else (
    echo %YLW%[1/7] Skipping Terraform (not installed)%RST%
    echo.
)

:: ============================================================
:: STEP 2 — BUILD DOCKER IMAGES
:: ============================================================
echo %CYN%[2/7] Building Docker images (this takes 5-10 min on first run)...%RST%
docker compose build
if errorlevel 1 (
    echo %RED%[FAIL] Docker build failed. Check output above.%RST%
    pause
    exit /b 1
)
echo %GRN%  [OK] Docker images built%RST%
echo.

:: ============================================================
:: STEP 3 — START LONG-RUNNING SERVICES
:: ============================================================
echo %CYN%[3/7] Starting long-running services (Redpanda, Flink, Dashboard)...%RST%
docker compose up -d redpanda redpanda-console redpanda-consumer flink-jobmanager flink-taskmanager dashboard
if errorlevel 1 (
    echo %RED%[FAIL] docker compose up failed.%RST%
    pause
    exit /b 1
)
echo %GRN%  [OK] Services started%RST%

:: Wait for Redpanda to be ready
echo %YLW%  Waiting 20 seconds for Redpanda to initialise...%RST%
timeout /t 20 /nobreak >nul
echo %GRN%  [OK] Redpanda should be ready%RST%
echo.

:: ============================================================
:: STEP 4 — CREATE REDPANDA TOPICS
:: ============================================================
echo %CYN%[4/7] Creating Redpanda topics...%RST%
docker compose exec redpanda rpk topic create eurostat.ingestion.completed --partitions 3 --replicas 1
docker compose exec redpanda rpk topic create eurostat.anomalies --partitions 3 --replicas 1
echo %GRN%  [OK] Topics created (errors about existing topics are safe to ignore)%RST%
echo.

:: ============================================================
:: STEP 5 — RUN dlt INGESTION
:: ============================================================
echo %CYN%[5/7] Step 1/3 - Running dlt ingestion (Eurostat API -> BigQuery raw)...%RST%
echo %YLW%  This may take 5-10 minutes on first run...%RST%
docker compose --profile pipeline run --rm dlt-ingestion
if errorlevel 1 (
    echo %RED%[FAIL] dlt ingestion failed. Check logs above.%RST%
    pause
    exit /b 1
)
echo %GRN%  [OK] Ingestion complete%RST%
echo.

:: ============================================================
:: STEP 6 — RUN SPARK BATCH JOB
:: ============================================================
echo %CYN%[6/7] Step 2/3 - Running Spark batch job (raw -> processed)...%RST%
docker compose --profile pipeline run --rm spark-batch
if errorlevel 1 (
    echo %RED%[FAIL] Spark batch job failed. Check logs above.%RST%
    pause
    exit /b 1
)
echo %GRN%  [OK] Spark batch complete%RST%
echo.

:: ============================================================
:: STEP 7 — RUN dbt TRANSFORMATIONS
:: ============================================================
echo %CYN%[7/7] Step 3/3 - Running dbt transformations (staging -> marts)...%RST%
docker compose --profile pipeline run --rm dbt
if errorlevel 1 (
    echo %RED%[FAIL] dbt failed. Check logs above. All 31 tests must pass.%RST%
    pause
    exit /b 1
)
echo %GRN%  [OK] dbt transformations complete%RST%