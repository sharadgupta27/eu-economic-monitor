@echo off
setlocal EnableDelayedExpansion
title EU Economic Monitor - Clean Project

cd /d "%~dp0"

echo.
echo ============================================================
echo   EU Economic Monitor - Clean Project
echo ============================================================
echo.
echo  This script offers two clean levels:
echo.
echo   [1] Soft clean  - stop containers, remove volumes ^& orphans
echo                     (keeps Docker images, keeps GCP resources)
echo.
echo   [2] Hard clean  - everything in soft clean PLUS removes all
echo                     project Docker images and build cache
echo                     (keeps GCP resources; re-run run_pipeline.bat
echo                      to rebuild from scratch)
echo.
echo   [3] Full reset  - everything in hard clean PLUS destroys GCP
echo                     infrastructure via Terraform
echo                     *** THIS DELETES ALL BIGQUERY DATA ***
echo.
echo   [Q] Quit - do nothing
echo.
set /p CHOICE="Enter choice [1/2/3/Q]: "

if /i "%CHOICE%"=="Q" exit /b 0
if /i "%CHOICE%"=="q" exit /b 0

:: ============================================================
:: Docker running check (needed for all levels)
:: ============================================================
docker info >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Docker is not running. Start Docker Desktop and try again.
    pause
    exit /b 1
)

:: ============================================================
:: SOFT CLEAN (level 1, 2, 3)
:: ============================================================
echo.
echo Stopping and removing containers, networks, and volumes...
docker compose down --volumes --remove-orphans
if errorlevel 1 (
    echo   [WARN] docker compose down reported errors (may be safe to ignore if already stopped)
)
echo   [OK] Containers and volumes removed

if "%CHOICE%"=="1" goto :DONE

:: ============================================================
:: HARD CLEAN - remove project images + build cache (level 2, 3)
:: ============================================================
echo.
echo Removing project Docker images...

:: Remove images by label (all images built by this compose project)
for /f "tokens=*" %%i in ('docker images --filter "reference=final_project*" -q 2^>nul') do (
    docker rmi -f %%i >nul 2>&1
)
for /f "tokens=*" %%i in ('docker images --filter "reference=eurostat*" -q 2^>nul') do (
    docker rmi -f %%i >nul 2>&1
)

:: Prune dangling images and build cache
echo Pruning dangling images and build cache...
docker image prune -f
docker builder prune -f
echo   [OK] Docker images and build cache cleaned

if "%CHOICE%"=="2" goto :DONE

:: ============================================================
:: FULL RESET - destroy GCP infrastructure (level 3 only)
:: ============================================================
echo.
echo ============================================================
echo   WARNING: This will DESTROY all GCP resources:
echo     - BigQuery datasets (all data lost)
echo     - GCS bucket (all data lost)
echo     - Service accounts
echo ============================================================
echo.
set /p CONFIRM="Type YES to confirm GCP destruction: "
if not "%CONFIRM%"=="YES" (
    echo Cancelled. GCP resources were NOT destroyed.
    goto :DONE
)

terraform version >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Terraform not found. Cannot destroy GCP resources.
    echo        Run: terraform destroy -var-file=terraform.tfvars  manually from terraform^/.
    pause
    exit /b 1
)

echo Running terraform destroy...
cd terraform
terraform destroy -var-file=terraform.tfvars -auto-approve
if errorlevel 1 (
    echo [FAIL] terraform destroy failed. Check output above.
    cd ..
    pause
    exit /b 1
)
cd ..
echo   [OK] GCP infrastructure destroyed

:: ============================================================
:DONE
:: ============================================================
echo.
echo ============================================================
echo   Clean complete.
echo ============================================================
echo.
if "%CHOICE%"=="1" (
    echo   To restart the pipeline, run:  run_pipeline.bat
)
if "%CHOICE%"=="2" (
    echo   Docker images were removed. run_pipeline.bat will rebuild them on next run.
)
if "%CHOICE%"=="3" (
    echo   GCP infrastructure was destroyed. Re-provision with Terraform before next run.
)
echo.
pause
