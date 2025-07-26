# Système de Collecte de Données de Surveillance Système

## 📋 Description

Ce projet implémente un système complet de collecte et d'analyse de données de surveillance système composé d'un agent collecteur déployé sur des machines distantes et d'un serveur centralisé pour la réception et le stockage des données. Le système permet de monitorer en temps réel les performances et l'état des machines dans un environnement distribué.

## 🏗️ Architecture du Système

### Composants Principaux

1. **Agent Collecteur (`agent.py`)** : Agent déployé sur chaque machine à surveiller
2. **Serveur de Réception (`server.py`)** : Serveur centralisé pour la collecte des données
3. **Outils d'Analyse** : Scripts pour l'analyse et la visualisation des données collectées
4. **Traitement de Données Archivées** : Système de traitement des données zippées

### Architecture de Données

- **Données Statiques** : Informations sur la configuration matérielle (CPU, RAM, disque, BIOS, etc.)
- **Données Variables** : Métriques de performance en temps réel (utilisation CPU/mémoire, trafic réseau, etc.)
- **Base de Données MongoDB** : Stockage centralisé avec collections séparées pour les données statiques et variables

## 🚀 Fonctionnalités

### Agent Collecteur
- ✅ Collecte automatique des données système (CPU, mémoire, disque, réseau)
- ✅ Détection du type de machine (portable/desktop)
- ✅ Surveillance de la batterie et température
- ✅ Gestion des périphériques USB et interfaces réseau
- ✅ Détection des seuils d'utilisation des ressources
- ✅ Compression et envoi sécurisé des données
- ✅ Gestion des reconnexions et retry automatique
- ✅ Support multi-plateforme (Linux, Windows)

### Serveur de Réception
- ✅ Réception en temps réel des données des agents
- ✅ Génération automatique d'ID machine unique
- ✅ Stockage structuré dans MongoDB
- ✅ Gestion des connexions concurrentes (max 50)
- ✅ Nettoyage automatique des anciennes données
- ✅ Validation des données avec Pydantic
- ✅ Logging complet et gestion d'erreurs

### Outils d'Analyse
- 📊 Analyse complète des données statiques (matériel, OS, configurations)
- 📈 Analyse des données variables (performances, utilisation ressources)
- 📉 Génération de graphiques temporels pour les métriques clés
- 🔍 Identification des jours d'activité maximale/minimale

## 📦 Installation et Configuration

### Prérequis
- Python 3.8+
- MongoDB 4.4+
- Packages Python : `pymongo`, `psutil`, `pydantic`, `matplotlib`, `GPUtil`, `backoff`

### Installation des Dépendances
```bash
pip install pymongo psutil pydantic matplotlib GPUtil backoff
```

### Configuration MongoDB
```bash
# Démarrer MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
```

### Configuration du Serveur
1. Modifier les paramètres dans `server.py` :
```python
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 12345
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
```

2. Démarrer le serveur :
```bash
python3 server.py
```

### Configuration de l'Agent
1. Modifier l'adresse du serveur dans `agent.py` :
```python
SERVER_HOST = '192.168.1.165'  # IP du serveur
SERVER_PORT = 12345
```

2. Démarrer l'agent sur chaque machine :
```bash
python3 agent.py
```

## 📊 Utilisation des Outils d'Analyse

### Analyse des Données Statiques
```bash
python3 analyze_static_data.py
```
Génère un rapport complet sur :
- Types de machines (portable/desktop)
- Configurations matérielles (CPU, RAM, disque)
- Systèmes d'exploitation
- Fabricants BIOS et cartes mères

### Analyse des Données Variables
```bash
python3 analyze_variable_data.py
```
Fournit des statistiques sur :
- Jours d'activité maximale/minimale
- Utilisation CPU, mémoire, disque
- Trafic réseau et connectivité
- Dépassements de seuils

### Génération de Graphiques
```bash
python3 plot_machine_metrics.py
```
Crée des graphiques temporels pour :
- Utilisation CPU
- Consommation mémoire
- Usage disque
- Trafic réseau
- Nombre de processus
- Temps de fonctionnement

### Traitement de Données Archivées
```bash
python3 process_zipped_data.py /chemin/vers/archive.zip
```

## 📁 Structure des Données

### Collections MongoDB
- `static_data` : Données de configuration matérielle
- `variable_data` : Métriques de performance temps réel
- `machine_ids` : Registre des machines surveillées

### Format des Données Statiques
```json
{
  "machine_id": "25f34bf2862b2bba82be3089eb7e2d65",
  "os": {...},
  "cpu": {...},
  "memoire": {...},
  "disque": {...},
  "bios_carte_mere": {...},
  "gpu": {...},
  "interfaces_reseau": [...],
  "battery_initial": {...}
}
```

### Format des Données Variables
```json
{
  "machine_id": "25f34bf2862b2bba82be3089eb7e2d65",
  "timestamp": "2025-06-23 14:30:00",
  "cpu": {...},
  "memoire": {...},
  "disque": {...},
  "reseau": {...},
  "connexion_internet": true,
  "nombre_processus": 245,
  "seuil_atteint": {...}
}
```

## 📈 Visualisations Générées

Le système génère automatiquement des graphiques dans le dossier `plots/` :
- `cpu_usage_[machine_id]_[date].png`
- `memory_usage_[machine_id]_[date].png`
- `disk_usage_[machine_id]_[date].png`
- `network_traffic_[machine_id]_[date].png`
- `process_count_[machine_id]_[date].png`
- `uptime_[machine_id]_[date].png`

## 🔧 Configuration Avancée

### Paramètres de l'Agent
- `COLLECTION_INTERVAL` : Intervalle de collecte (défaut: 2s)
- `SEND_INTERVAL` : Intervalle d'envoi (défaut: 30s)
- `RESOURCE_THRESHOLD` : Seuil d'alerte ressources (défaut: 80%)
- `STORAGE_LIMIT` : Limite stockage local (défaut: 200MB)

### Paramètres du Serveur
- `MAX_CONCURRENT_CONNECTIONS` : Connexions simultanées max (défaut: 50)
- `DATA_RETENTION_DAYS` : Rétention données variables (défaut: 30 jours)

## 📊 Données Collectées

**[Le lien vers les données collectées sera ajouté ici]**

## 🐛 Dépannage

### Problèmes Courants
1. **Erreur de connexion MongoDB** : Vérifier que MongoDB est démarré
2. **Agent ne se connecte pas** : Vérifier l'IP/port du serveur
3. **Permissions insuffisantes** : Exécuter avec des privilèges appropriés pour certaines métriques

### Logs
- Agent : `system_monitor.log`
- Serveur : `server.log`
- Analyses : `*.log` dans chaque script

## 📝 Article de Recherche

Ce système a fait l'objet d'une publication scientifique détaillant les méthodologies de collecte, l'architecture distribuée et les résultats d'analyse des données de surveillance système dans un environnement multi-machines.

## 👥 Auteurs

- **Delibes** - Développement de l'agent collecteur
- **Équipe de recherche Master II** - Architecture système et analyse

## 📄 Licence

Ce projet est développé dans le cadre d'un projet de recherche Master II.

---

*Dernière mise à jour : Juillet 2025*