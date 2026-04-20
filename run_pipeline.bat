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
echo.

:: ============================================================
:: DONE
:: ============================================================
echo %CYN%============================================================%RST%
echo %GRN%  Pipeline complete!%RST%
echo %CYN%============================================================%RST%
echo.
echo   Dashboard:        http://localhost:8501
echo   Redpanda Console: http://localhost:8080
echo   Flink Web UI:     http://localhost:8081
echo.
echo %YLW%  Optional: run  flink-streaming.bat  to submit the PyFlink streaming job.%RST%
echo.

:: Open the dashboard in the default browser
start http://localhost:8501

pause
@echo off
setlocal EnableDelayedExpansion
title EU Economic Monitor - Full Pipeline

:: ============================================================
:: Resolve script directory so the batch file can be double-
:: clicked from anywhere and still find the project root.
:: ============================================================
cd /d "%~dp0"

echo.
echo ============================================================
echo   EU Economic Monitor - One-Click Pipeline Runner
echo ============================================================
echo.

:: ============================================================
:: Pre-flight checks
:: ============================================================
echo [CHECK] Verifying prerequisites...

where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed or not on PATH. Install Docker Desktop first.
    goto :fail
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop is not running. Please start it and re-run this script.
    goto :fail
)

where make >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 'make' not found. Install it via 'winget install GnuWin32.Make' or Git Bash.
    goto :fail
)

if not exist ".env" (
    echo [ERROR] .env file not found. Run 'make setup' and fill in your GCP values.
    goto :fail
)

if not exist "credentials\service-account.json" (
    echo [ERROR] credentials\service-account.json not found.
    echo        Download your GCP service account key and place it there.
    goto :fail
)

echo [OK] All prerequisites satisfied.
echo.

:: ============================================================
:: STEP 1 - Verify / apply Terraform (GCP infrastructure)
:: ============================================================
call :step 1 9 "Verifying GCP infrastructure via Terraform..."
where terraform >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 'terraform' not found on PATH.
    echo        Install from https://developer.hashicorp.com/terraform/downloads
    goto :fail
)
if not exist "terraform\terraform.tfstate" (
    echo           No tfstate found - provisioning GCP infrastructure now...
    cd terraform
    terraform init -input=false
    if errorlevel 1 ( cd .. & goto :fail )
    terraform apply -var-file=terraform.tfvars -auto-approve
    if errorlevel 1 ( cd .. & goto :fail )
    cd ..
    echo           GCP infrastructure provisioned successfully.
) else (
    echo           tfstate found - infrastructure already provisioned.
    echo           Running 'terraform plan' to check for drift...
    cd terraform
    terraform plan -var-file=terraform.tfvars -detailed-exitcode >nul 2>&1
    set TF_EXIT=!errorlevel!
    cd ..
    if !TF_EXIT!==0 echo           No infrastructure changes needed.
    if !TF_EXIT!==1 (
        echo [ERROR] Terraform plan failed. Run 'make terraform-plan' for details.
        goto :fail
    )
    if !TF_EXIT!==2 (
        echo           Drift detected - applying changes...
        cd terraform
        terraform apply -var-file=terraform.tfvars -auto-approve
        if errorlevel 1 ( cd .. & goto :fail )
        cd ..
        echo           Infrastructure updated.
    )
)
call :ok

:: ============================================================
:: STEP 2 - Build Docker images
:: ============================================================
call :step 2 9 "Checking Docker images (building only if missing or changed)..."
docker image inspect eurostat-pyflink >nul 2>&1 && docker image inspect final_project-redpanda-consumer >nul 2>&1 && docker image inspect final_project-dashboard >nul 2>&1
if errorlevel 1 (
    echo           Images not found - building now...
    make build
    if errorlevel 1 goto :fail
) else (
    echo           All images present - skipping build. Run 'make build' to update.
)
call :ok

:: ============================================================
:: STEP 3 - Start long-running services
:: ============================================================
call :step 3 9 "Starting services: Redpanda, Flink cluster, Consumer, Dashboard..."
make up
if errorlevel 1 goto :fail
call :ok

:: ============================================================
:: STEP 4 - Wait for Redpanda to be ready
:: ============================================================
call :step 4 9 "Waiting for Redpanda to become healthy (up to 60s)..."
set /a wait=0
:wait_redpanda
docker compose ps redpanda 2>nul | findstr "healthy" >nul
if errorlevel 1 (
    set /a wait+=5
    if !wait! geq 60 (
        echo [ERROR] Redpanda did not become healthy within 60 seconds.
        goto :fail
    )
    timeout /t 5 /nobreak >nul
    goto :wait_redpanda
)
call :ok

:: ============================================================
:: STEP 5 - Create Redpanda topics (idempotent - safe to re-run)
:: ============================================================
call :step 5 9 "Creating Redpanda topics..."
make create-topics
:: topic-already-exists errors are non-fatal
call :ok

:: ============================================================
:: STEP 6 - Wait for Flink cluster to be ready
:: ============================================================
call :step 6 9 "Waiting for Flink JobManager to become healthy (up to 90s)..."
set /a wait=0
:wait_flink
docker compose ps flink-jobmanager 2>nul | findstr "healthy" >nul
if errorlevel 1 (
    set /a wait+=5
    if !wait! geq 90 (
        echo [ERROR] Flink JobManager did not become healthy within 90 seconds.
        goto :fail
    )
    timeout /t 5 /nobreak >nul
    goto :wait_flink
)
call :ok

:: ============================================================
:: STEP 7 - Submit PyFlink streaming job
:: ============================================================
call :step 7 9 "Submitting PyFlink streaming job..."
make flink-streaming
if errorlevel 1 goto :fail
call :ok

:: ============================================================
:: STEP 8 - Run batch pipeline (ingest → Spark → dbt)
:: ============================================================
call :step 8 9 "Running batch pipeline: dlt ingestion → Spark → dbt..."
echo    This may take 10-30 minutes depending on data volume.
make pipeline
if errorlevel 1 goto :fail
call :ok

:: ============================================================
:: STEP 9 - Open dashboard
:: ============================================================
call :step 9 9 "Opening Streamlit dashboard..."
start "" "http://localhost:8501"
start "" "http://localhost:8080"
start "" "http://localhost:8081"
call :ok

:: ============================================================
:: Done
:: ============================================================
echo.
echo ============================================================
echo   Pipeline complete!
echo ============================================================
echo.
echo   Dashboard:        http://localhost:8501
echo   Redpanda Console: http://localhost:8080
echo   Flink Web UI:     http://localhost:8081
echo.
echo   To stop all services:  make down
echo.
pause
exit /b 0

:: ============================================================
:: Helpers
:: ============================================================
:step
echo [STEP %1/%2] %~3
exit /b 0

:ok
echo           Done.
echo.
exit /b 0

:fail
echo.
echo ============================================================
echo   Pipeline failed. Check the output above for details.
echo ============================================================
echo.
echo   Useful commands:
echo     make logs     - tail all service logs
echo     make down     - stop all containers
echo.
pause
exit /b 1
