#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to plot time-series metrics for a machine with RAM >= 16GB and >= 8 logical cores
on the most active day. Generates plots for CPU, memory, disk, network, and processes.
"""

import re
from pymongo import MongoClient
import logging
from typing import Dict, List
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import traceback
import os

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('plot_machine_metrics.log'),
        logging.StreamHandler()
    ]
)

# MongoDB Configuration
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
DATABASE_NAME = 'machine_monitoring'
STATIC_COLLECTION = 'static_data'
VARIABLE_COLLECTION = 'variable_data'

# Most active day from analyze_variable_data.py
MOST_ACTIVE_DAY = '2025-06-23'  # Updated based on user input

def parse_memory_size(memory_str: str) -> float:
    """Convert memory string (e.g., '7.68 GB') to GB as float."""
    try:
        if not memory_str or memory_str == 'Non disponible':
            return 0.0
        match = re.match(r'(\d+\.?\d*)\s*(GB|MB|TB)', memory_str, re.IGNORECASE)
        if not match:
            logging.warning(f"Invalid memory format: {memory_str}")
            return 0.0
        value, unit = float(match.group(1)), match.group(2).upper()
        if unit == 'MB':
            return value / 1024.0
        elif unit == 'TB':
            return value * 1024.0
        return value
    except Exception as e:
        logging.error(f"Error parsing memory size '{memory_str}': {e}\n{traceback.format_exc()}")
        return 0.0

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

def parse_uptime(uptime_str: str) -> float:
    """Convert uptime string (e.g., '1 day, 2:30:00' or '4:32:15.568523') to seconds."""
    try:
        if not uptime_str or uptime_str == 'Non disponible':
            return 0.0
        # Split on comma for cases with days
        parts = uptime_str.split(',')
        days = 0
        time_str = parts[-1].strip()  # Get the time part (last element)
        
        # Check for days
        if len(parts) > 1 and 'day' in parts[0].lower():
            days = int(parts[0].split()[0])
        
        # Split time part into hours, minutes, seconds (ignoring microseconds)
        time_parts = time_str.split(':')
        if len(time_parts) != 3:
            logging.warning(f"Invalid uptime format: {uptime_str}")
            return 0.0
        
        hours, minutes, seconds_str = time_parts
        # Remove microseconds (if present) by taking only the integer part of seconds
        seconds = int(float(seconds_str.split('.')[0]))
        
        return days * 86400 + int(hours) * 3600 + int(minutes) * 60 + seconds
    except Exception as e:
        logging.error(f"Error parsing uptime '{uptime_str}': {e}\n{traceback.format_exc()}")
        return 0.0

def select_machine() -> str:
    """Select a machine with RAM >= 16GB and >= 8 logical cores."""
    try:
        client = MongoClient(MONGO_HOST, MONGO_PORT)
        db = client[DATABASE_NAME]
        static_collection = db[STATIC_COLLECTION]

        # Fetch all machines to inspect RAM and cores
        machines = static_collection.find(
            {},
            {'machine_id': 1, 'memoire.ram.total': 1, 'cpu.coeurs_logiques': 1, '_id': 0}
        )

        qualifying_machines = []
        for machine in machines:
            ram_str = machine.get('memoire', {}).get('ram', {}).get('total', '0 GB')
            ram = parse_memory_size(ram_str)
            cores = machine.get('cpu', {}).get('coeurs_logiques', 0) or 0
            if ram >= 16 and cores >= 8:
                qualifying_machines.append(machine['machine_id'])
            else:
                logging.debug(f"Machine {machine['machine_id']}: RAM {ram} GB, Cores {cores} - does not qualify")

        client.close()

        if qualifying_machines:
            selected_machine = qualifying_machines[0]  # Select first qualifying machine
            logging.info(f"Selected machine {selected_machine} with RAM >= 16GB and >= 8 logical cores")
            return selected_machine
        else:
            logging.warning("No machine found with RAM >= 16GB and >= 8 logical cores")
            return None
    except Exception as e:
        logging.error(f"Error selecting machine: {e}\n{traceback.format_exc()}")
        return None

def fetch_machine_data(machine_id: str, day: str) -> List[Dict]:
    """Fetch variable data for the specified machine and day."""
    try:
        client = MongoClient(MONGO_HOST, MONGO_PORT)
        db = client[DATABASE_NAME]
        variable_collection = db[VARIABLE_COLLECTION]

        start_date = datetime.strptime(day, '%Y-%m-%d')
        end_date = start_date + timedelta(days=1)

        data = variable_collection.find(
            {
                'machine_id': machine_id,
                'timestamp': {
                    '$gte': start_date,
                    '$lt': end_date
                }
            },
            {
                'timestamp': 1,
                'cpu.global_utilise': 1,
                'memoire.ram.pourcentage_utilise': 1,
                'disque.pourcentage_utilise': 1,
                'reseau.octets_envoyes': 1,
                'reseau.octets_recus': 1,
                'nombre_processus': 1,
                'uptime': 1,
                '_id': 0
            }
        ).sort('timestamp', 1)

        data_list = list(data)
        client.close()
        return data_list
    except Exception as e:
        logging.error(f"Error fetching machine data: {e}\n{traceback.format_exc()}")
        return []

def plot_metrics(data: List[Dict], machine_id: str, day: str):
    """Plot time-series metrics for the specified machine and day."""
    try:
        if not data:
            logging.error("No data to plot")
            return

        timestamps = [doc['timestamp'] for doc in data]
        cpu_usage = [doc.get('cpu', {}).get('global_utilise', 0.0) or 0.0 for doc in data]
        mem_used = [doc.get('memoire', {}).get('ram', {}).get('pourcentage_utilise', 0.0) or 0.0 for doc in data]
        mem_free = [100.0 - m if m <= 100.0 else 0.0 for m in mem_used]
        disk_used = [doc.get('disque', {}).get('pourcentage_utilise', 0.0) or 0.0 for doc in data]
        disk_free = [100.0 - d if d <= 100.0 else 0.0 for d in disk_used]
        net_sent = [parse_network_traffic(doc.get('reseau', {}).get('octets_envoyes', '0 MB')) for doc in data]
        net_received = [parse_network_traffic(doc.get('reseau', {}).get('octets_recus', '0 MB')) for doc in data]
        processes = [doc.get('nombre_processus', 0) or 0 for doc in data]
        uptime = [parse_uptime(doc.get('uptime', '0')) for doc in data]

        # Create output directory
        os.makedirs('plots', exist_ok=True)

        # Plot 1: CPU Usage
        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, cpu_usage, label='CPU Usage (%)', color='#4CAF50', linewidth=2)
        plt.title(f'CPU Usage for Machine {machine_id} on {day}', fontsize=14)
        plt.xlabel('Time', fontsize=12)
        plt.ylabel('Usage (%)', fontsize=12)
        plt.grid(True)
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f'plots/cpu_usage_{machine_id}_{day}.png')
        plt.close()

        # Plot 2: Memory Usage
        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, mem_used, label='Memory Used (%)', color='#2196F3', linewidth=2)
        plt.plot(timestamps, mem_free, label='Memory Free (%)', color='#FF9800', linewidth=2, linestyle='--')
        plt.title(f'Memory Usage for Machine {machine_id} on {day}', fontsize=14)
        plt.xlabel('Time', fontsize=12)
        plt.ylabel('Percentage (%)', fontsize=12)
        plt.grid(True)
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f'plots/memory_usage_{machine_id}_{day}.png')
        plt.close()

        # Plot 3: Disk Usage
        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, disk_used, label='Disk Used (%)', color='#9C27B0', linewidth=2)
        plt.plot(timestamps, disk_free, label='Disk Free (%)', color='#FF5722', linewidth=2, linestyle='--')
        plt.title(f'Disk Usage for Machine {machine_id} on {day}', fontsize=14)
        plt.xlabel('Time', fontsize=12)
        plt.ylabel('Percentage (%)', fontsize=12)
        plt.grid(True)
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f'plots/disk_usage_{machine_id}_{day}.png')
        plt.close()

        # Plot 4: Network Traffic
        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, net_sent, label='Network Sent (MB)', color='#009688', linewidth=2)
        plt.plot(timestamps, net_received, label='Network Received (MB)', color='#F44336', linewidth=2)
        plt.title(f'Network Traffic for Machine {machine_id} on {day}', fontsize=14)
        plt.xlabel('Time', fontsize=12)
        plt.ylabel('Traffic (MB)', fontsize=12)
        plt.grid(True)
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f'plots/network_traffic_{machine_id}_{day}.png')
        plt.close()

        # Plot 5: Process Count
        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, processes, label='Process Count', color='#607D8B', linewidth=2)
        plt.title(f'Process Count for Machine {machine_id} on {day}', fontsize=14)
        plt.xlabel('Time', fontsize=12)
        plt.ylabel('Number of Processes', fontsize=12)
        plt.grid(True)
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f'plots/process_count_{machine_id}_{day}.png')
        plt.close()

        # Plot 6: Uptime
        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, uptime, label='Uptime (Seconds)', color='#795548', linewidth=2)
        plt.title(f'Uptime for Machine {machine_id} on {day}', fontsize=14)
        plt.xlabel('Time', fontsize=12)
        plt.ylabel('Uptime (Seconds)', fontsize=12)
        plt.grid(True)
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f'plots/uptime_{machine_id}_{day}.png')
        plt.close()

        logging.info(f"Plots generated for machine {machine_id} on {day} in 'plots' directory")

    except Exception as e:
        logging.error(f"Error plotting metrics: {e}\n{traceback.format_exc()}")

def main():
    """Main function to select machine and plot metrics."""
    try:
        machine_id = select_machine()
        if not machine_id:
            logging.error("No qualifying machine found. Please check static_data.")
            return

        data = fetch_machine_data(machine_id, MOST_ACTIVE_DAY)
        if not data:
            logging.error(f"No variable data found for machine {machine_id} on {MOST_ACTIVE_DAY}")
            return

        plot_metrics(data, machine_id, MOST_ACTIVE_DAY)
    except Exception as e:
        logging.error(f"Error in main: {e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()