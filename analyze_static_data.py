#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to comprehensively analyze static data from machine_monitoring database.
Covers machine types, OS, CPU, RAM, disk, BIOS, GPU, network interfaces, battery, and more.
"""

import re
from pymongo import MongoClient
import logging
from typing import Dict, List, Tuple
from collections import defaultdict
import traceback

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('static_data_analysis.log'),
        logging.StreamHandler()
    ]
)

# MongoDB Configuration
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
DATABASE_NAME = 'machine_monitoring'
STATIC_COLLECTION = 'static_data'

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

def parse_frequency(freq: str) -> float:
    """Convert frequency string (e.g., '1800') to MHz as float."""
    try:
        if not freq or freq == 'Non disponible':
            return 0.0
        return float(freq)
    except Exception as e:
        logging.error(f"Error parsing frequency '{freq}': {e}\n{traceback.format_exc()}")
        return 0.0

def parse_network_speed(speed_str: str) -> float:
    """Convert network speed string (e.g., '1000 Mbps') to Mbps as float."""
    try:
        if not speed_str or speed_str == 'Non disponible':
            return 0.0
        match = re.match(r'(\d+\.?\d*)\s*(Mbps|Gbps)', speed_str, re.IGNORECASE)
        if not match:
            logging.warning(f"Invalid network speed format: {speed_str}")
            return 0.0
        value, unit = float(match.group(1)), match.group(2).upper()
        if unit == 'Gbps':
            return value * 1000.0
        return value
    except Exception as e:
        logging.error(f"Error parsing network speed '{speed_str}': {e}\n{traceback.format_exc()}")
        return 0.0

def analyze_static_data() -> Dict:
    """Analyze static data from MongoDB and return comprehensive statistics."""
    try:
        # Connect to MongoDB
        client = MongoClient(MONGO_HOST, MONGO_PORT)
        db = client[DATABASE_NAME]
        collection = db[STATIC_COLLECTION]

        # Initialize result dictionary
        results = {
            'total_machines': 0,
            'machine_types': {'laptop': 0, 'desktop': 0},
            'os': {
                'types': defaultdict(int),
                'versions': defaultdict(int),
                'releases': defaultdict(int)
            },
            'ram': {
                'total_gb': 0.0,
                'average_gb': 0.0,
                'distribution': defaultdict(int)
            },
            'cpu': {
                'physical_cores': {'total': 0, 'average': 0.0, 'distribution': defaultdict(int)},
                'logical_cores': {'total': 0, 'average': 0.0, 'distribution': defaultdict(int)},
                'frequency': {
                    'min': {'total': 0.0, 'average': 0.0, 'distribution': defaultdict(int)},
                    'max': {'total': 0.0, 'average': 0.0, 'distribution': defaultdict(int)},
                    'current': {'total': 0.0, 'average': 0.0, 'distribution': defaultdict(int)}
                }
            },
            'disk': {
                'total_gb': 0.0,
                'average_gb': 0.0,
                'distribution': defaultdict(int)
            },
            'bios': {
                'bios_manufacturer': defaultdict(int),
                'motherboard_manufacturer': defaultdict(int)
            },
            'gpu': {
                'has_gpu': 0,
                'names': defaultdict(int),
                'ram': {'total_gb': 0.0, 'average_gb': 0.0, 'distribution': defaultdict(int)}
            },
            'network_interfaces': {
                'total_count': 0,
                'total_speed_mbps': 0.0,
                'average_speed_mbps': 0.0,
                'distribution': defaultdict(int)
            },
            'battery': {
                'has_battery': 0,
                'distribution': defaultdict(int)
            }
        }

        # Fetch all static data
        machines = collection.find({}, {
            'type_machine': 1,
            'os': 1,
            'cpu': 1,
            'memoire': 1,
            'disque': 1,
            'bios_carte_mere': 1,
            'gpu': 1,
            'interfaces_reseau': 1,
            'battery_initial': 1,
            '_id': 0
        })

        machine_count = 0
        ram_values = []
        disk_values = []
        physical_cores = []
        logical_cores = []
        freq_min = []
        freq_max = []
        freq_current = []
        gpu_ram_values = []
        network_speeds = []
        network_interfaces_count = []

        for machine in machines:
            machine_count += 1

            # Machine type
            machine_type = 'laptop' if machine.get('type_machine') == 0 else 'desktop'
            results['machine_types'][machine_type] += 1

            # OS details
            os_info = machine.get('os', {})
            os_type = os_info.get('nom', 'Unknown')
            os_version = os_info.get('version', 'Unknown')
            os_release = os_info.get('release', 'Unknown')
            results['os']['types'][os_type] += 1
            results['os']['versions'][f"{os_type} {os_version}"] += 1
            results['os']['releases'][f"{os_type} {os_release}"] += 1

            # RAM
            ram_str = machine.get('memoire', {}).get('ram', {}).get('total', '0 GB')
            ram_gb = parse_memory_size(ram_str)
            ram_values.append(ram_gb)
            ram_key = round(ram_gb)
            results['ram']['distribution'][ram_key] += 1

            # CPU
            cpu_info = machine.get('cpu', {})
            phys_cores = cpu_info.get('coeurs_physiques', 0) or 0
            log_cores = cpu_info.get('coeurs_logiques', 0) or 0
            physical_cores.append(phys_cores)
            logical_cores.append(log_cores)
            results['cpu']['physical_cores']['distribution'][phys_cores] += 1
            results['cpu']['logical_cores']['distribution'][log_cores] += 1

            # CPU Frequencies
            freq_info = cpu_info.get('frequence', {})
            f_min = parse_frequency(freq_info.get('min', '0'))
            f_max = parse_frequency(freq_info.get('max', '0'))
            f_current = parse_frequency(freq_info.get('actuelle', '0'))
            freq_min.append(f_min)
            freq_max.append(f_max)
            freq_current.append(f_current)
            results['cpu']['frequency']['min']['distribution'][round(f_min / 100) * 100] += 1
            results['cpu']['frequency']['max']['distribution'][round(f_max / 100) * 100] += 1
            results['cpu']['frequency']['current']['distribution'][round(f_current / 100) * 100] += 1

            # Disk
            disk_str = machine.get('disque', {}).get('total', '0 GB')
            disk_gb = parse_memory_size(disk_str)
            disk_values.append(disk_gb)
            disk_key = round(disk_gb / 100) * 100  # Group by 100GB increments
            results['disk']['distribution'][disk_key] += 1

            # BIOS
            bios_info = machine.get('bios_carte_mere', {})
            bios_manufacturer = bios_info.get('BIOS', {}).get('Fabricant', 'Unknown')
            mb_manufacturer = bios_info.get('Carte mère', {}).get('Fabricant', 'Unknown')
            results['bios']['bios_manufacturer'][bios_manufacturer] += 1
            results['bios']['motherboard_manufacturer'][mb_manufacturer] += 1

            # GPU
            gpu_info = machine.get('gpu', {})
            if gpu_info.get('Disponible', False):
                results['gpu']['has_gpu'] += 1
                gpu_name = gpu_info.get('Nom', 'Unknown')
                results['gpu']['names'][gpu_name] += 1
                gpu_ram_str = gpu_info.get('RAM', '0 GB')
                gpu_ram_gb = parse_memory_size(gpu_ram_str)
                gpu_ram_values.append(gpu_ram_gb)
                gpu_ram_key = round(gpu_ram_gb)
                results['gpu']['ram']['distribution'][gpu_ram_key] += 1

            # Network Interfaces
            interfaces = machine.get('interfaces_reseau', [])
            interface_count = len(interfaces)
            network_interfaces_count.append(interface_count)
            total_speed = 0.0
            for interface in interfaces:
                speed = parse_network_speed(interface.get('vitesse', '0 Mbps'))
                total_speed += speed
                results['network_interfaces']['distribution'][round(speed / 100) * 100] += 1
            network_speeds.append(total_speed)

            # Battery
            battery_info = machine.get('battery_initial', {})
            has_battery = battery_info.get('has_battery') == 0
            results['battery']['has_battery'] += 1 if has_battery else 0
            results['battery']['distribution']['With Battery' if has_battery else 'No Battery'] += 1

        # Calculate totals and averages
        results['total_machines'] = machine_count
        if machine_count > 0:
            results['ram']['total_gb'] = sum(ram_values)
            results['ram']['average_gb'] = results['ram']['total_gb'] / machine_count
            results['disk']['total_gb'] = sum(disk_values)
            results['disk']['average_gb'] = results['disk']['total_gb'] / machine_count
            results['cpu']['physical_cores']['total'] = sum(physical_cores)
            results['cpu']['physical_cores']['average'] = results['cpu']['physical_cores']['total'] / machine_count
            results['cpu']['logical_cores']['total'] = sum(logical_cores)
            results['cpu']['logical_cores']['average'] = results['cpu']['logical_cores']['total'] / machine_count
            results['cpu']['frequency']['min']['total'] = sum(freq_min)
            results['cpu']['frequency']['min']['average'] = results['cpu']['frequency']['min']['total'] / machine_count
            results['cpu']['frequency']['max']['total'] = sum(freq_max)
            results['cpu']['frequency']['max']['average'] = results['cpu']['frequency']['max']['total'] / machine_count
            results['cpu']['frequency']['current']['total'] = sum(freq_current)
            results['cpu']['frequency']['current']['average'] = results['cpu']['frequency']['current']['total'] / machine_count
            results['gpu']['ram']['total_gb'] = sum(gpu_ram_values)
            results['gpu']['ram']['average_gb'] = results['gpu']['ram']['total_gb'] / results['gpu']['has_gpu'] if results['gpu']['has_gpu'] > 0 else 0.0
            results['network_interfaces']['total_count'] = sum(network_interfaces_count)
            results['network_interfaces']['total_speed_mbps'] = sum(network_speeds)
            results['network_interfaces']['average_speed_mbps'] = results['network_interfaces']['total_speed_mbps'] / machine_count if machine_count > 0 else 0.0

        # Convert defaultdict to regular dict
        for key in ['os', 'ram', 'cpu', 'disk', 'bios', 'gpu', 'network_interfaces', 'battery']:
            for subkey, value in results[key].items():
                if isinstance(value, defaultdict):
                    results[key][subkey] = dict(value)
                elif isinstance(value, dict):
                    for subsubkey, subvalue in value.items():
                        if isinstance(subvalue, defaultdict):
                            results[key][subkey][subsubkey] = dict(subvalue)

        client.close()
        return results

    except Exception as e:
        logging.error(f"Error analyzing static data: {e}\n{traceback.format_exc()}")
        return {}

def print_analysis(results: Dict):
    """Print the analysis results in a formatted way."""
    print("\n=== Comprehensive Static Data Analysis ===")
    print(f"Total Machines: {results.get('total_machines', 0)}")
    
    print("\nMachine Types:")
    for mtype, count in results['machine_types'].items():
        print(f"  {mtype.capitalize()}: {count}")
    
    print("\nOS Statistics:")
    print("  OS Types:")
    for os, count in sorted(results['os']['types'].items()):
        print(f"    {os}: {count}")
    print("  OS Versions:")
    for version, count in sorted(results['os']['versions'].items()):
        print(f"    {version}: {count}")
    print("  OS Releases:")
    for release, count in sorted(results['os']['releases'].items()):
        print(f"    {release}: {count}")
    
    print("\nRAM Statistics:")
    print(f"  Total RAM: {results['ram']['total_gb']:.2f} GB")
    print(f"  Average RAM per Machine: {results['ram']['average_gb']:.2f} GB")
    print("  RAM Distribution (GB):")
    for ram, count in sorted(results['ram']['distribution'].items()):
        print(f"    {ram} GB: {count} machines")
    
    print("\nCPU Statistics:")
    print("  Physical Cores:")
    print(f"    Total: {results['cpu']['physical_cores']['total']}")
    print(f"    Average per Machine: {results['cpu']['physical_cores']['average']:.2f}")
    print("    Distribution:")
    for cores, count in sorted(results['cpu']['physical_cores']['distribution'].items()):
        print(f"      {cores} cores: {count} machines")
    print("  Logical Cores:")
    print(f"    Total: {results['cpu']['logical_cores']['total']}")
    print(f"    Average per Machine: {results['cpu']['logical_cores']['average']:.2f}")
    print("    Distribution:")
    for cores, count in sorted(results['cpu']['logical_cores']['distribution'].items()):
        print(f"      {cores} cores: {count} machines")
    print("  CPU Frequency (MHz):")
    print("    Min Frequency:")
    print(f"      Total: {results['cpu']['frequency']['min']['total']:.2f} MHz")
    print(f"      Average: {results['cpu']['frequency']['min']['average']:.2f} MHz")
    print("      Distribution:")
    for freq, count in sorted(results['cpu']['frequency']['min']['distribution'].items()):
        print(f"        {freq} MHz: {count} machines")
    print("    Max Frequency:")
    print(f"      Total: {results['cpu']['frequency']['max']['total']:.2f} MHz")
    print(f"      Average: {results['cpu']['frequency']['max']['average']:.2f} MHz")
    print("      Distribution:")
    for freq, count in sorted(results['cpu']['frequency']['max']['distribution'].items()):
        print(f"        {freq} MHz: {count} machines")
    print("    Current Frequency:")
    print(f"      Total: {results['cpu']['frequency']['current']['total']:.2f} MHz")
    print(f"      Average: {results['cpu']['frequency']['current']['average']:.2f} MHz")
    print("      Distribution:")
    for freq, count in sorted(results['cpu']['frequency']['current']['distribution'].items()):
        print(f"        {freq} MHz: {count} machines")
    
    print("\nDisk Statistics:")
    print(f"  Total Disk Capacity: {results['disk']['total_gb']:.2f} GB")
    print(f"  Average Disk Capacity per Machine: {results['disk']['average_gb']:.2f} GB")
    print("  Disk Capacity Distribution (GB):")
    for disk, count in sorted(results['disk']['distribution'].items()):
        print(f"    {disk} GB: {count} machines")
    
    print("\nBIOS and Motherboard Manufacturers:")
    print("  BIOS Manufacturer:")
    for manu, count in sorted(results['bios']['bios_manufacturer'].items()):
        print(f"    {manu}: {count}")
    print("  Motherboard Manufacturer:")
    for manu, count in sorted(results['bios']['motherboard_manufacturer'].items()):
        print(f"    {manu}: {count}")
    
    print("\nGPU Statistics:")
    print(f"  Machines with GPU: {results['gpu']['has_gpu']}")
    print("  GPU Names:")
    for name, count in sorted(results['gpu']['names'].items()):
        print(f"    {name}: {count}")
    print(f"  Total GPU RAM: {results['gpu']['ram']['total_gb']:.2f} GB")
    print(f"  Average GPU RAM per GPU Machine: {results['gpu']['ram']['average_gb']:.2f} GB")
    print("  GPU RAM Distribution (GB):")
    for ram, count in sorted(results['gpu']['ram']['distribution'].items()):
        print(f"    {ram} GB: {count} machines")
    
    print("\nNetwork Interfaces Statistics:")
    print(f"  Total Interfaces: {results['network_interfaces']['total_count']}")
    print(f"  Total Speed: {results['network_interfaces']['total_speed_mbps']:.2f} Mbps")
    print(f"  Average Speed per Machine: {results['network_interfaces']['average_speed_mbps']:.2f} Mbps")
    print("  Interface Speed Distribution (Mbps):")
    for speed, count in sorted(results['network_interfaces']['distribution'].items()):
        print(f"    {speed} Mbps: {count} interfaces")
    
    print("\nBattery Statistics:")
    print(f"  Machines with Battery: {results['battery']['has_battery']}")
    print("  Battery Distribution:")
    for status, count in sorted(results['battery']['distribution'].items()):
        print(f"    {status}: {count}")
    
    print("====================================\n")

def main():
    """Main function to run the analysis."""
    try:
        results = analyze_static_data()
        if results:
            print_analysis(results)
        else:
            logging.error("No results returned from analysis")
    except Exception as e:
        logging.error(f"Error in main: {e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()