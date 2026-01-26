<<<<<<< Updated upstream
# Script de Vérification du Setup FraudGuard
# Usage: .\check-setup.ps1

Write-Host "=== Vérification du Setup FraudGuard ===" -ForegroundColor Cyan
Write-Host ""

# Fonction pour afficher le statut
function Show-Status {
    param(
        [string]$Item,
        [bool]$Success,
        [string]$Details = ""
    )
    if ($Success) {
        Write-Host "[OK]" -ForegroundColor Green -NoNewline
        Write-Host " $Item" -NoNewline
        if ($Details) {
            Write-Host " - $Details" -ForegroundColor Gray
        } else {
            Write-Host ""
        }
    } else {
        Write-Host "[X]" -ForegroundColor Red -NoNewline
        Write-Host " $Item" -NoNewline
        if ($Details) {
            Write-Host " - $Details" -ForegroundColor Yellow
        } else {
            Write-Host ""
        }
    }
}

# 1. Vérifier Python
Write-Host "1. Python" -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Show-Status "Python installé" $true $pythonVersion
} catch {
    Show-Status "Python installé" $false "Non trouvé"
}
Write-Host ""

# 2. Vérifier les dépendances Python
Write-Host "2. Dépendances Python" -ForegroundColor Yellow
$packages = @("numpy", "pandas", "scikit-learn", "lightgbm", "fastapi", "uvicorn")
foreach ($pkg in $packages) {
    try {
        $version = pip show $pkg 2>$null | Select-String "Version:" | ForEach-Object { $_.Line.Split(":")[1].Trim() }
        if ($version) {
            Show-Status "$pkg" $true $version
        } else {
            Show-Status "$pkg" $false "Non installé"
        }
    } catch {
        Show-Status "$pkg" $false "Erreur de vérification"
    }
}
Write-Host ""

# 3. Vérifier Docker
Write-Host "3. Docker" -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    Show-Status "Docker installé" $true $dockerVersion

    # Vérifier si Docker daemon est lancé
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Show-Status "Docker daemon actif" $true
    } else {
        Show-Status "Docker daemon actif" $false "Docker Desktop doit être lancé"
    }
} catch {
    Show-Status "Docker installé" $false "Non trouvé - Voir INSTALL_DOCKER.md"
}

try {
    $composeVersion = docker compose version 2>&1
    Show-Status "Docker Compose installé" $true $composeVersion
} catch {
    Show-Status "Docker Compose installé" $false
}
Write-Host ""

# 4. Vérifier les données Kaggle
Write-Host "4. Données Kaggle" -ForegroundColor Yellow
$fraudTrain = Test-Path "artifacts/data/fraudTrain.csv"
$fraudTest = Test-Path "artifacts/data/fraudTest.csv"

Show-Status "fraudTrain.csv" $fraudTrain $(if ($fraudTrain) { "335 MB" } else { "Manquant" })
Show-Status "fraudTest.csv" $fraudTest $(if ($fraudTest) { "144 MB" } else { "Manquant" })
Write-Host ""

# 5. Vérifier les fichiers de configuration
Write-Host "5. Configuration" -ForegroundColor Yellow
$envFile = Test-Path ".env"
$dockerCompose = Test-Path "docker-compose.yml"

Show-Status ".env" $envFile
Show-Status "docker-compose.yml" $dockerCompose
Write-Host ""

# 6. Vérifier les services (si Docker tourne)
Write-Host "6. Services Docker" -ForegroundColor Yellow
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        $containers = docker compose ps --format json 2>&1 | ConvertFrom-Json
        if ($containers) {
            foreach ($container in $containers) {
                $running = $container.State -eq "running"
                Show-Status $container.Service $running $container.State
            }
        } else {
            Write-Host "Aucun conteneur en cours d'exécution" -ForegroundColor Gray
            Write-Host "Pour démarrer: docker compose up -d" -ForegroundColor Gray
        }
    } else {
        Write-Host "Docker daemon non actif - impossible de vérifier les services" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Impossible de vérifier les services" -ForegroundColor Yellow
}
Write-Host ""

# Résumé
Write-Host "=== Résumé ===" -ForegroundColor Cyan
Write-Host ""

$allOk = $true

# Vérifier les prérequis critiques
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Python n'est pas installé" -ForegroundColor Red
    $allOk = $false
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Docker n'est pas installé - Voir INSTALL_DOCKER.md" -ForegroundColor Red
    $allOk = $false
} else {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Docker Desktop n'est pas lancé" -ForegroundColor Red
        $allOk = $false
    }
}

if (-not $fraudTrain -or -not $fraudTest) {
    Write-Host "[!] Données Kaggle manquantes - Voir CLAUDE.md" -ForegroundColor Red
    $allOk = $false
}

if ($allOk) {
    Write-Host "[OK] Setup complet - Prêt à démarrer!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Pour démarrer les services:" -ForegroundColor Cyan
    Write-Host "  docker compose up -d" -ForegroundColor White
    Write-Host ""
    Write-Host "Pour vérifier la santé:" -ForegroundColor Cyan
    Write-Host "  curl http://localhost:8000/health" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "Setup incomplet - Veuillez corriger les erreurs ci-dessus" -ForegroundColor Yellow
    Write-Host "Consultez SETUP_STATUS.md pour plus de détails" -ForegroundColor Gray
}
=======
# Script de Vérification du Setup SafeGuard
# Usage: .\check-setup.ps1

Write-Host "=== Vérification du Setup SafeGuard ===" -ForegroundColor Cyan
Write-Host ""

# Fonction pour afficher le statut
function Show-Status {
    param(
        [string]$Item,
        [bool]$Success,
        [string]$Details = ""
    )
    if ($Success) {
        Write-Host "[OK]" -ForegroundColor Green -NoNewline
        Write-Host " $Item" -NoNewline
        if ($Details) {
            Write-Host " - $Details" -ForegroundColor Gray
        } else {
            Write-Host ""
        }
    } else {
        Write-Host "[X]" -ForegroundColor Red -NoNewline
        Write-Host " $Item" -NoNewline
        if ($Details) {
            Write-Host " - $Details" -ForegroundColor Yellow
        } else {
            Write-Host ""
        }
    }
}

# 1. Vérifier Python
Write-Host "1. Python" -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Show-Status "Python installé" $true $pythonVersion
} catch {
    Show-Status "Python installé" $false "Non trouvé"
}
Write-Host ""

# 2. Vérifier les dépendances Python
Write-Host "2. Dépendances Python" -ForegroundColor Yellow
$packages = @("numpy", "pandas", "scikit-learn", "lightgbm", "fastapi", "uvicorn")
foreach ($pkg in $packages) {
    try {
        $version = pip show $pkg 2>$null | Select-String "Version:" | ForEach-Object { $_.Line.Split(":")[1].Trim() }
        if ($version) {
            Show-Status "$pkg" $true $version
        } else {
            Show-Status "$pkg" $false "Non installé"
        }
    } catch {
        Show-Status "$pkg" $false "Erreur de vérification"
    }
}
Write-Host ""

# 3. Vérifier Docker
Write-Host "3. Docker" -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    Show-Status "Docker installé" $true $dockerVersion

    # Vérifier si Docker daemon est lancé
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Show-Status "Docker daemon actif" $true
    } else {
        Show-Status "Docker daemon actif" $false "Docker Desktop doit être lancé"
    }
} catch {
    Show-Status "Docker installé" $false "Non trouvé - Voir INSTALL_DOCKER.md"
}

try {
    $composeVersion = docker compose version 2>&1
    Show-Status "Docker Compose installé" $true $composeVersion
} catch {
    Show-Status "Docker Compose installé" $false
}
Write-Host ""

# 4. Vérifier les données Kaggle
Write-Host "4. Données Kaggle" -ForegroundColor Yellow
$fraudTrain = Test-Path "artifacts/data/fraudTrain.csv"
$fraudTest = Test-Path "artifacts/data/fraudTest.csv"

Show-Status "fraudTrain.csv" $fraudTrain $(if ($fraudTrain) { "335 MB" } else { "Manquant" })
Show-Status "fraudTest.csv" $fraudTest $(if ($fraudTest) { "144 MB" } else { "Manquant" })
Write-Host ""

# 5. Vérifier les fichiers de configuration
Write-Host "5. Configuration" -ForegroundColor Yellow
$envFile = Test-Path ".env"
$dockerCompose = Test-Path "docker-compose.yml"

Show-Status ".env" $envFile
Show-Status "docker-compose.yml" $dockerCompose
Write-Host ""

# 6. Vérifier les services (si Docker tourne)
Write-Host "6. Services Docker" -ForegroundColor Yellow
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        $containers = docker compose ps --format json 2>&1 | ConvertFrom-Json
        if ($containers) {
            foreach ($container in $containers) {
                $running = $container.State -eq "running"
                Show-Status $container.Service $running $container.State
            }
        } else {
            Write-Host "Aucun conteneur en cours d'exécution" -ForegroundColor Gray
            Write-Host "Pour démarrer: docker compose up -d" -ForegroundColor Gray
        }
    } else {
        Write-Host "Docker daemon non actif - impossible de vérifier les services" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Impossible de vérifier les services" -ForegroundColor Yellow
}
Write-Host ""

# Résumé
Write-Host "=== Résumé ===" -ForegroundColor Cyan
Write-Host ""

$allOk = $true

# Vérifier les prérequis critiques
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Python n'est pas installé" -ForegroundColor Red
    $allOk = $false
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Docker n'est pas installé - Voir INSTALL_DOCKER.md" -ForegroundColor Red
    $allOk = $false
} else {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Docker Desktop n'est pas lancé" -ForegroundColor Red
        $allOk = $false
    }
}

if (-not $fraudTrain -or -not $fraudTest) {
    Write-Host "[!] Données Kaggle manquantes - Voir CLAUDE.md" -ForegroundColor Red
    $allOk = $false
}

if ($allOk) {
    Write-Host "[OK] Setup complet - Prêt à démarrer!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Pour démarrer les services:" -ForegroundColor Cyan
    Write-Host "  docker compose up -d" -ForegroundColor White
    Write-Host ""
    Write-Host "Pour vérifier la santé:" -ForegroundColor Cyan
    Write-Host "  curl http://localhost:8000/health" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "Setup incomplet - Veuillez corriger les erreurs ci-dessus" -ForegroundColor Yellow
    Write-Host "Consultez SETUP_STATUS.md pour plus de détails" -ForegroundColor Gray
}
>>>>>>> Stashed changes
