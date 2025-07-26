# System Monitoring Data Collection Project

## 📋 Description

This project implements a comprehensive system monitoring data collection and analysis system composed of a collector agent deployed on remote machines and a centralized server for data reception and storage. The system enables real-time monitoring of machine performance and status in a distributed environment.

## 🏗️ System Architecture

### Main Components

1. **Collector Agent (`agent.py`)** : Agent deployed on each machine to monitor
2. **Reception Server (`server.py`)** : Centralized server for data collection
3. **Analysis Tools** : Scripts for data analysis and visualization
4. **Archived Data Processing** : System for processing zipped data

### Data Architecture

- **Static Data** : Hardware configuration information (CPU, RAM, disk, BIOS, etc.)
- **Variable Data** : Real-time performance metrics (CPU/memory usage, network traffic, etc.)
- **MongoDB Database** : Centralized storage with separate collections for static and variable data

## 🚀 Features

### Collector Agent
- ✅ Automatic system data collection (CPU, memory, disk, network)
- ✅ Machine type detection (laptop/desktop)
- ✅ Battery and temperature monitoring
- ✅ USB devices and network interfaces management
- ✅ Resource usage threshold detection
- ✅ Compressed and secure data transmission
- ✅ Automatic reconnection and retry management
- ✅ Cross-platform support (Linux, Windows)

### Reception Server
- ✅ Real-time data reception from agents
- ✅ Automatic unique machine ID generation
- ✅ Structured storage in MongoDB
- ✅ Concurrent connection management (max 50)
- ✅ Automatic cleanup of old data
- ✅ Data validation with Pydantic
- ✅ Comprehensive logging and error handling

### Analysis Tools
- 📊 Complete static data analysis (hardware, OS, configurations)
- 📈 Variable data analysis (performance, resource usage)
- 📉 Time-series graph generation for key metrics
- 🔍 Maximum/minimum activity day identification

## 📦 Installation and Configuration

### Prerequisites
- Python 3.8+
- MongoDB 4.4+
- Python packages: `pymongo`, `psutil`, `pydantic`, `matplotlib`, `GPUtil`, `backoff`

### Dependencies Installation
```bash
pip install -r requirements.txt
```

### MongoDB Configuration
```bash
# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
```

### Server Configuration
1. Modify parameters in `server.py`:
```python
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 12345
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
```

2. Start the server:
```bash
python3 server.py
```

### Agent Configuration
1. Modify server address in `agent.py`:
```python
SERVER_HOST = '192.168.1.165'  # Server IP
SERVER_PORT = 12345
```

2. Start the agent on each machine:
```bash
python3 agent.py
```

## 📊 Analysis Tools Usage

### Static Data Analysis
```bash
python3 analyze_static_data.py
```
Generates a comprehensive report on:
- Machine types (laptop/desktop)
- Hardware configurations (CPU, RAM, disk)
- Operating systems
- BIOS and motherboard manufacturers

### Variable Data Analysis
```bash
python3 analyze_variable_data.py
```
Provides statistics on:
- Maximum/minimum activity days
- CPU, memory, disk usage
- Network traffic and connectivity
- Threshold breaches

### Graph Generation
```bash
python3 plot_machine_metrics.py
```
Creates time-series graphs for:
- CPU usage
- Memory consumption
- Disk usage
- Network traffic
- Process count
- Uptime

### Archived Data Processing
```bash
python3 process_zipped_data.py /path/to/archive.zip
```

## 📁 Data Structure

### MongoDB Collections
- `static_data` : Hardware configuration data
- `variable_data` : Real-time performance metrics
- `machine_ids` : Registry of monitored machines

### Static Data Format
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

### Variable Data Format
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

## 📈 Generated Visualizations

The system automatically generates graphs in the `plots/` folder:
- `cpu_usage_[machine_id]_[date].png`
- `memory_usage_[machine_id]_[date].png`
- `disk_usage_[machine_id]_[date].png`
- `network_traffic_[machine_id]_[date].png`
- `process_count_[machine_id]_[date].png`
- `uptime_[machine_id]_[date].png`

## 🔧 Advanced Configuration

### Agent Parameters
- `COLLECTION_INTERVAL` : Collection interval (default: 2s)
- `SEND_INTERVAL` : Send interval (default: 30s)
- `RESOURCE_THRESHOLD` : Resource alert threshold (default: 80%)
- `STORAGE_LIMIT` : Local storage limit (default: 200MB)

### Server Parameters
- `MAX_CONCURRENT_CONNECTIONS` : Max simultaneous connections (default: 50)
- `DATA_RETENTION_DAYS` : Variable data retention (default: 30 days)

## 📊 Collected Data

The collected data is available in multiple formats:

### CSV Exports
- **Machine Registry**: [`exports/machine_ids.csv`](exports/machine_ids.csv) - Complete list of monitored machines
- **Static Data**: [`exports/static_data.csv`](exports/static_data.csv) - Hardware configurations and system information
- **Variable Data**: [`exports/variable_data.csv`](exports/variable_data.csv) - Performance metrics and monitoring data

### MongoDB Dump
- **Complete Database**: [`exports/machine_monitoring/`](exports/machine_monitoring/) - Full MongoDB export in BSON format
  - `machine_ids.bson` - Machine registry collection
  - `static_data.bson` - Static data collection
  - `variable_data.bson` - Variable data collection
  - Associated metadata files (`.metadata.json`)

### Sample Visualizations
The `plots/` directory contains sample visualizations generated from the collected data:
- CPU usage trends
- Memory consumption patterns
- Disk utilization
- Network traffic analysis
- Process count evolution
- System uptime tracking

## 🐛 Troubleshooting

### Common Issues
1. **MongoDB connection error** : Check that MongoDB is running
2. **Agent cannot connect** : Verify server IP/port
3. **Insufficient permissions** : Run with appropriate privileges for certain metrics

### Logs
- Agent: `system_monitor.log`
- Server: `server.log`
- Analysis: `*.log` in each script

## 📝 Research Publication

This system has been the subject of a scientific publication detailing collection methodologies, distributed architecture, and system monitoring data analysis results in a multi-machine environment.

## 👥 Authors

- **Delibes** - Collector agent development
- **System and Networking Research Team or UY1** - System architecture and analysis
- **Serge Noah**: - [Sergenoah000](mailto:gaetan.noah@facsciences-uy1.cm) Supervision
- **Kitwé Adagao** - Author


## 📄 License

This project is developed as part of a Master II research project.

---

*Last updated: July 2025*