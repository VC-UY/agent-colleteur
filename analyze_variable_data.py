#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to analyze variable data from machine_monitoring database.
Identifies days with most/least machines powered on and calculates min/max/avg for variable metrics.
"""

import re
from pymongo import MongoClient
import logging
from typing import Dict
from collections import defaultdict
from datetime import datetime
import traceback

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('variable_data_analysis.log'),
        logging.StreamHandler()
    ]
)

# MongoDB Configuration
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
DATABASE_NAME = 'machine_monitoring'
VARIABLE_COLLECTION = 'variable_data'
MACHINE_IDS_COLLECTION = 'machine_ids'

def parse_network_traffic(traffic_str: str) -> float:
    """Convert network traffic string (e.g., '1.23 MB') to MB as float."""
    try:
        if not traffic_str or traffic_str == 'Non disponible':
            return 0.0
        match = re.match(r'(\d+\.?\d*)\s*(MB|GB|KB)', traffic_str, re.IGNORECASE)
        if not match:
            logging.warning(f"Invalid traffic format: {traffic_str}")
            return 0.0
        value, unit = float(match.group(1)), match.group(2).upper()
        if unit == 'KB':
            return value / 1024.0
        elif unit == 'GB':
            return value * 1024.0
        return value
    except Exception as e:
        logging.error(f"Error parsing network traffic '{traffic_str}': {e}\n{traceback.format_exc()}")
        return 0.0

def analyze_variable_data() -> Dict:
    """Analyze variable data from MongoDB and return statistics."""
    try:
        # Connect to MongoDB
        client = MongoClient(MONGO_HOST, MONGO_PORT)
        db = client[DATABASE_NAME]
        variable_collection = db[VARIABLE_COLLECTION]
        machine_ids_collection = db[MACHINE_IDS_COLLECTION]

        # Initialize result dictionary
        results = {
            'machine_activity': {
                'by_day': defaultdict(set),
                'most_active_day': {'day': '', 'count': 0},
                'least_active_day': {'day': '', 'count': float('inf')}
            },
            'metrics': {
                'cpu_usage_percent': {'min': float('inf'), 'max': 0.0, 'avg': 0.0, 'count': 0},
                'memory_used_percent': {'min': float('inf'), 'max': 0.0, 'avg': 0.0, 'count': 0},
                'memory_free_percent': {'min': float('inf'), 'max': 0.0, 'avg': 0.0, 'count': 0},
                'disk_used_percent': {'min': float('inf'), 'max': 0.0, 'avg': 0.0, 'count': 0},
                'disk_free_percent': {'min': float('inf'), 'max': 0.0, 'avg': 0.0, 'count': 0},
                'network_sent_mb': {'min': float('inf'), 'max': 0.0, 'avg': 0.0, 'count': 0},
                'network_received_mb': {'min': float('inf'), 'max': 0.0, 'avg': 0.0, 'count': 0},
                'process_count': {'min': float('inf'), 'max': 0.0, 'avg': 0.0, 'count': 0},
                'uptime_seconds': {'min': float('inf'), 'max': 0.0, 'avg': 0.0, 'count': 0},
                'internet_connectivity': {'connected_count': 0, 'total_count': 0, 'percentage': 0.0},
                'threshold_breaches': {'cpu': 0, 'memory': 0, 'disk': 0, 'total': 0}
            }
        }

        # Fetch variable data
        documents = variable_collection.find({}, {
            'machine_id': 1,
            'timestamp': 1,
            'cpu.global_utilise': 1,
            'memoire.ram.pourcentage_utilise': 1,
            'disque.pourcentage_utilise': 1,
            'reseau.octets_envoyes': 1,
            'reseau.octets_recus': 1,
            'nombre_processus': 1,
            'uptime': 1,
            'connexion_internet': 1,
            'seuil_atteint': 1,
            '_id': 0
        })

        # Process machine activity by day
        for doc in documents:
            timestamp = doc.get('timestamp')
            machine_id = doc.get('machine_id')
            if timestamp and machine_id:
                day = timestamp.strftime('%Y-%m-%d')
                results['machine_activity']['by_day'][day].add(machine_id)

        # Calculate most and least active days
        for day, machines in results['machine_activity']['by_day'].items():
            count = len(machines)
            if count > results['machine_activity']['most_active_day']['count']:
                results['machine_activity']['most_active_day'] = {'day': day, 'count': count}
            if count < results['machine_activity']['least_active_day']['count']:
                results['machine_activity']['least_active_day'] = {'day': day, 'count': count}

        # Reset cursor to process metrics
        documents = variable_collection.find({}, {
            'cpu.global_utilise': 1,
            'memoire.ram.pourcentage_utilise': 1,
            'disque.pourcentage_utilise': 1,
            'reseau.octets_envoyes': 1,
            'reseau.octets_recus': 1,
            'nombre_processus': 1,
            'uptime': 1,
            'connexion_internet': 1,
            'seuil_atteint': 1,
            '_id': 0
        })

        # Initialize accumulators
        cpu_sum = 0
        mem_sum = 0
        disk_sum = 0
        sent_sum = 0
        received_sum = 0
        process_sum = 0
        uptime_sum = 0
        total_docs = 0

        for doc in documents:
            total_docs += 1

            # CPU Usage
            cpu = doc.get('cpu', {}).get('global_utilise', 0.0) or 0.0
            results['metrics']['cpu_usage_percent']['min'] = min(results['metrics']['cpu_usage_percent']['min'], cpu)
            results['metrics']['cpu_usage_percent']['max'] = max(results['metrics']['cpu_usage_percent']['max'], cpu)
            cpu_sum += cpu

            # Memory Usage
            mem_used = doc.get('memoire', {}).get('ram', {}).get('pourcentage_utilise', 0.0) or 0.0
            mem_free = 100.0 - mem_used if mem_used <= 100.0 else 0.0
            results['metrics']['memory_used_percent']['min'] = min(results['metrics']['memory_used_percent']['min'], mem_used)
            results['metrics']['memory_used_percent']['max'] = max(results['metrics']['memory_used_percent']['max'], mem_used)
            results['metrics']['memory_free_percent']['min'] = min(results['metrics']['memory_free_percent']['min'], mem_free)
            results['metrics']['memory_free_percent']['max'] = max(results['metrics']['memory_free_percent']['max'], mem_free)
            mem_sum += mem_used

            # Disk Usage
            disk_used = doc.get('disque', {}).get('pourcentage_utilise', 0.0) or 0.0
            disk_free = 100.0 - disk_used if disk_used <= 100.0 else 0.0
            results['metrics']['disk_used_percent']['min'] = min(results['metrics']['disk_used_percent']['min'], disk_used)
            results['metrics']['disk_used_percent']['max'] = max(results['metrics']['disk_used_percent']['max'], disk_used)
            results['metrics']['disk_free_percent']['min'] = min(results['metrics']['disk_free_percent']['min'], disk_free)
            results['metrics']['disk_free_percent']['max'] = max(results['metrics']['disk_free_percent']['max'], disk_free)
            disk_sum += disk_used

            # Network Traffic
            sent = parse_network_traffic(doc.get('reseau', {}).get('octets_envoyes', '0 MB'))
            received = parse_network_traffic(doc.get('reseau', {}).get('octets_recus', '0 MB'))
            results['metrics']['network_sent_mb']['min'] = min(results['metrics']['network_sent_mb']['min'], sent)
            results['metrics']['network_sent_mb']['max'] = max(results['metrics']['network_sent_mb']['max'], sent)
            results['metrics']['network_received_mb']['min'] = min(results['metrics']['network_received_mb']['min'], received)
            results['metrics']['network_received_mb']['max'] = max(results['metrics']['network_received_mb']['max'], received)
            sent_sum += sent
            received_sum += received

            # Process Count
            processes = doc.get('nombre_processus', 0) or 0
            results['metrics']['process_count']['min'] = min(results['metrics']['process_count']['min'], processes)
            results['metrics']['process_count']['max'] = max(results['metrics']['process_count']['max'], processes)
            process_sum += processes

            # Uptime (convert to seconds)
            uptime_str = doc.get('uptime', '0') or '0'
            try:
                parts = uptime_str.split(',')
                days = int(parts[0].split()[0]) if 'day' in uptime_str else 0
                time_parts = parts[-1].strip().split(':')
                hours, minutes, seconds = map(int, time_parts)
                uptime_secs = days * 86400 + hours * 3600 + minutes * 60 + seconds
            except:
                uptime_secs = 0
            results['metrics']['uptime_seconds']['min'] = min(results['metrics']['uptime_seconds']['min'], uptime_secs)
            results['metrics']['uptime_seconds']['max'] = max(results['metrics']['uptime_seconds']['max'], uptime_secs)
            uptime_sum += uptime_secs

            # Internet Connectivity
            connected = doc.get('connexion_internet', False)
            results['metrics']['internet_connectivity']['connected_count'] += 1 if connected else 0
            results['metrics']['internet_connectivity']['total_count'] += 1

            # Threshold Breaches
            thresholds = doc.get('seuil_atteint', {})
            if thresholds.get('cpu', False):
                results['metrics']['threshold_breaches']['cpu'] += 1
            if thresholds.get('memory', False):
                results['metrics']['threshold_breaches']['memory'] += 1
            if thresholds.get('disk', False):
                results['metrics']['threshold_breaches']['disk'] += 1
            results['metrics']['threshold_breaches']['total'] += sum(1 for k, v in thresholds.items() if v)

        # Calculate averages
        if total_docs > 0:
            results['metrics']['cpu_usage_percent']['avg'] = cpu_sum / total_docs
            results['metrics']['memory_used_percent']['avg'] = mem_sum / total_docs
            results['metrics']['memory_free_percent']['avg'] = 100.0 - results['metrics']['memory_used_percent']['avg']
            results['metrics']['disk_used_percent']['avg'] = disk_sum / total_docs
            results['metrics']['disk_free_percent']['avg'] = 100.0 - results['metrics']['disk_used_percent']['avg']
            results['metrics']['network_sent_mb']['avg'] = sent_sum / total_docs
            results['metrics']['network_received_mb']['avg'] = received_sum / total_docs
            results['metrics']['process_count']['avg'] = process_sum / total_docs
            results['metrics']['uptime_seconds']['avg'] = uptime_sum / total_docs
            results['metrics']['internet_connectivity']['percentage'] = (
                results['metrics']['internet_connectivity']['connected_count'] / 
                results['metrics']['internet_connectivity']['total_count'] * 100
            ) if results['metrics']['internet_connectivity']['total_count'] > 0 else 0.0

        # Set counts for metrics
        for metric in ['cpu_usage_percent', 'memory_used_percent', 'memory_free_percent', 
                       'disk_used_percent', 'disk_free_percent', 'network_sent_mb', 
                       'network_received_mb', 'process_count', 'uptime_seconds']:
            results['metrics'][metric]['count'] = total_docs

        # Handle case with no data
        for metric in ['cpu_usage_percent', 'memory_used_percent', 'memory_free_percent', 
                       'disk_used_percent', 'disk_free_percent', 'network_sent_mb', 
                       'network_received_mb', 'process_count', 'uptime_seconds']:
            if results['metrics'][metric]['count'] == 0:
                results['metrics'][metric]['min'] = 0.0
                results['metrics'][metric]['max'] = 0.0
                results['metrics'][metric]['avg'] = 0.0

        client.close()
        return results

    except Exception as e:
        logging.error(f"Error analyzing variable data: {e}\n{traceback.format_exc()}")
        return {}

def print_analysis(results: Dict):
    """Print the analysis results in a formatted way."""
    print("\n=== Variable Data Analysis ===")
    print("\nMachine Activity by Day:")
    print(f"  Most Active Day: {results['machine_activity']['most_active_day']['day']} "
          f"({results['machine_activity']['most_active_day']['count']} machines)")
    print(f"  Least Active Day: {results['machine_activity']['least_active_day']['day']} "
          f"({results['machine_activity']['least_active_day']['count']} machines)")
    
    print("\nResource Metrics:")
    print("  CPU Usage (%):")
    print(f"    Min: {results['metrics']['cpu_usage_percent']['min']:.2f}%")
    print(f"    Max: {results['metrics']['cpu_usage_percent']['max']:.2f}%")
    print(f"    Average: {results['metrics']['cpu_usage_percent']['avg']:.2f}%")
    print(f"    Data Points: {results['metrics']['cpu_usage_percent']['count']}")
    
    print("  Memory Usage (%):")
    print(f"    Min Used: {results['metrics']['memory_used_percent']['min']:.2f}%")
    print(f"    Max Used: {results['metrics']['memory_used_percent']['max']:.2f}%")
    print(f"    Average Used: {results['metrics']['memory_used_percent']['avg']:.2f}%")
    print(f"    Min Free: {results['metrics']['memory_free_percent']['min']:.2f}%")
    print(f"    Max Free: {results['metrics']['memory_free_percent']['max']:.2f}%")
    print(f"    Average Free: {results['metrics']['memory_free_percent']['avg']:.2f}%")
    print(f"    Data Points: {results['metrics']['memory_used_percent']['count']}")
    
    print("  Disk Usage (%):")
    print(f"    Min Used: {results['metrics']['disk_used_percent']['min']:.2f}%")
    print(f"    Max Used: {results['metrics']['disk_used_percent']['max']:.2f}%")
    print(f"    Average Used: {results['metrics']['disk_used_percent']['avg']:.2f}%")
    print(f"    Min Free: {results['metrics']['disk_free_percent']['min']:.2f}%")
    print(f"    Max Free: {results['metrics']['disk_free_percent']['max']:.2f}%")
    print(f"    Average Free: {results['metrics']['disk_free_percent']['avg']:.2f}%")
    print(f"    Data Points: {results['metrics']['disk_used_percent']['count']}")
    
    print("  Network Traffic (MB):")
    print(f"    Sent - Min: {results['metrics']['network_sent_mb']['min']:.2f} MB")
    print(f"    Sent - Max: {results['metrics']['network_sent_mb']['max']:.2f} MB")
    print(f"    Sent - Average: {results['metrics']['network_sent_mb']['avg']:.2f} MB")
    print(f"    Received - Min: {results['metrics']['network_received_mb']['min']:.2f} MB")
    print(f"    Received - Max: {results['metrics']['network_received_mb']['max']:.2f} MB")
    print(f"    Received - Average: {results['metrics']['network_received_mb']['avg']:.2f} MB")
    print(f"    Data Points: {results['metrics']['network_sent_mb']['count']}")
    
    print("  Process Count:")
    print(f"    Min: {results['metrics']['process_count']['min']}")
    print(f"    Max: {results['metrics']['process_count']['max']}")
    print(f"    Average: {results['metrics']['process_count']['avg']:.2f}")
    print(f"    Data Points: {results['metrics']['process_count']['count']}")
    
    print("  Uptime (Seconds):")
    print(f"    Min: {results['metrics']['uptime_seconds']['min']:.0f} seconds")
    print(f"    Max: {results['metrics']['uptime_seconds']['max']:.0f} seconds")
    print(f"    Average: {results['metrics']['uptime_seconds']['avg']:.0f} seconds")
    print(f"    Data Points: {results['metrics']['uptime_seconds']['count']}")
    
    print("  Internet Connectivity:")
    print(f"    Connected Data Points: {results['metrics']['internet_connectivity']['connected_count']}")
    print(f"    Total Data Points: {results['metrics']['internet_connectivity']['total_count']}")
    print(f"    Connectivity Percentage: {results['metrics']['internet_connectivity']['percentage']:.2f}%")
    
    print("  Threshold Breaches:")
    print(f"    CPU Breaches: {results['metrics']['threshold_breaches']['cpu']}")
    print(f"    Memory Breaches: {results['metrics']['threshold_breaches']['memory']}")
    print(f"    Disk Breaches: {results['metrics']['threshold_breaches']['disk']}")
    print(f"    Total Breaches: {results['metrics']['threshold_breaches']['total']}")
    
    print("=============================\n")

def main():
    """Main function to run the analysis."""
    try:
        results = analyze_variable_data()
        if results:
            print_analysis(results)
        else:
            logging.error("No results returned from analysis")
    except Exception as e:
        logging.error(f"Error in main: {e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()