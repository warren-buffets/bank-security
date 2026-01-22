# Guide d'Installation Docker Desktop pour Windows

## Étape 1: Télécharger Docker Desktop

1. Allez sur https://www.docker.com/products/docker-desktop/
2. Cliquez sur "Download for Windows"
3. Le fichier `Docker Desktop Installer.exe` sera téléchargé

## Étape 2: Installer Docker Desktop

1. Lancez `Docker Desktop Installer.exe`
2. Suivez l'assistant d'installation
3. Assurez-vous que l'option "Use WSL 2 instead of Hyper-V" est cochée (recommandé pour Windows 10/11)
4. Cliquez sur "Ok" pour commencer l'installation
5. Attendez que l'installation se termine

## Étape 3: Redémarrer l'Ordinateur

Docker Desktop nécessite un redémarrage pour finaliser l'installation.

## Étape 4: Démarrer Docker Desktop

1. Lancez Docker Desktop depuis le menu Démarrer
2. Attendez que Docker démarre (icône Docker dans la barre des tâches devient verte)
3. Vous pouvez voir le statut dans l'interface Docker Desktop

## Étape 5: Vérifier l'Installation

Ouvrez Git Bash ou PowerShell et exécutez:

```bash
docker --version
docker compose version
```

Vous devriez voir les versions installées, par exemple:
```
Docker version 24.0.7, build afdd53b
Docker Compose version v2.23.3
```

## Étape 6: Configuration Recommandée

### Allouer des Ressources

1. Ouvrez Docker Desktop
2. Allez dans Settings (icône engrenage)
3. Onglet "Resources"
4. Recommandations pour FraudGuard:
   - **CPUs**: Minimum 4, recommandé 6+
   - **Memory**: Minimum 8 GB, recommandé 12 GB+
   - **Swap**: 2 GB
   - **Disk image size**: 60 GB minimum

### Activer WSL 2 (Windows 10/11)

Si vous n'avez pas WSL 2:
1. Ouvrez PowerShell en tant qu'administrateur
2. Exécutez:
```powershell
wsl --install
```
3. Redémarrez votre PC
4. Dans Docker Desktop Settings > General, cochez "Use the WSL 2 based engine"

## Étape 7: Tester Docker avec FraudGuard

Une fois Docker installé et démarré:

```bash
# Naviguer vers le projet
cd "c:\Users\fpvmo\OneDrive - Epitech\Projet 5ème année\bank-security"

# Démarrer tous les services
docker compose up -d

# Vérifier que les conteneurs sont lancés
docker compose ps

# Voir les logs
docker compose logs -f
```

## Dépannage

### "Docker daemon is not running"
- Assurez-vous que Docker Desktop est lancé
- Vérifiez l'icône dans la barre des tâches (elle doit être verte)

### "WSL 2 installation is incomplete"
- Installez WSL 2 avec la commande PowerShell ci-dessus
- Redémarrez votre PC

### "Not enough memory"
- Augmentez la mémoire allouée dans Docker Desktop Settings > Resources

### Les conteneurs ne démarrent pas
```bash
# Nettoyer et redémarrer
docker compose down -v
docker compose up -d --build
```

## Ressources

- Documentation officielle: https://docs.docker.com/desktop/install/windows-install/
- WSL 2: https://learn.microsoft.com/en-us/windows/wsl/install
- Support Docker: https://docs.docker.com/desktop/troubleshoot/overview/
