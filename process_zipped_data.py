#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to process a zipped system-monitor folder and save data to MongoDB.
Handles both static and variable data, using machine_id from machine_id.txt or generating it from 1.json.gz.
Skips empty or invalid JSON files with appropriate logging.
"""

import os
import zipfile
import gzip
import json
import hashlib
import tempfile
import shutil
import logging
from datetime import datetime, timedelta
from pymongo import MongoClient
from pydantic import BaseModel, ValidationError
import traceback

# Configuration
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
DATABASE_NAME = 'machine_monitoring'
STATIC_COLLECTION = 'static_data'
VARIABLE_COLLECTION = 'variable_data'
MACHINE_IDS_COLLECTION = 'machine_ids'
DATA_RETENTION_DAYS = 30

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('process_zipped_data.log'),
        logging.StreamHandler()
    ]
)

class StaticData(BaseModel):
    os: dict
    cpu: dict
    memoire: dict
    bios_carte_mere: dict
    utilisateurs_connectes: list
    adresse_mac: str

class ZipDataProcessor:
    def __init__(self):
        try:
            self.mongo_client = MongoClient(MONGO_HOST, MONGO_PORT)
            self.db = self.mongo_client[DATABASE_NAME]
            self.static_collection = self.db[STATIC_COLLECTION]
            self.variable_collection = self.db[VARIABLE_COLLECTION]
            self.machine_ids_collection = self.db[MACHINE_IDS_COLLECTION]
            self.static_collection.create_index("machine_id")
            self.variable_collection.create_index([("machine_id", 1), ("timestamp", 1)])
            self.machine_ids_collection.create_index("machine_id", unique=True)
            logging.info("MongoDB connection established")
            # self.cleanup_old_data()
            self.machine_id = None  # Store machine_id for use across files
        except Exception as e:
            logging.error(f"Error connecting to MongoDB: {e}\n{traceback.format_exc()}")
            raise

    def generate_machine_id(self, static_data):
        """Generate a machine ID based on static characteristics (same as server.py)."""
        try:
            os_info = static_data.get('os', {})
            cpu_info = static_data.get('cpu', {})
            bios_info = static_data.get('bios_carte_mere', {})
            memoire_info = static_data.get('memoire', {})
            users = static_data.get('utilisateurs_connectes', [])
            username = users[0].get('username', '') if users else ''
            unique_string = (
                f"{os_info.get('hostname', '')}"
                f"{os_info.get('nom', '')}"
                f"{os_info.get('release', '')}"
                f"{os_info.get('version', '')}"
                f"{username}"
                f"{cpu_info.get('coeurs_logiques', 0)}"
                f"{cpu_info.get('frequence', {}).get('min', 0)}"
                f"{cpu_info.get('frequence', {}).get('max', 0)}"
                f"{bios_info.get('BIOS', {}).get('Fabricant', '')}"
                f"{bios_info.get('BIOS', {}).get('Version', '')}"
                f"{bios_info.get('Carte mère', {}).get('Fabricant', '')}"
                f"{bios_info.get('Carte mère', {}).get('Modèle', '')}"
                f"{memoire_info.get('ram', {}).get('total', '')}"
            )
            return hashlib.md5(unique_string.encode('utf-8')).hexdigest()
        except Exception as e:
            logging.error(f"Error generating machine ID: {e}\n{traceback.format_exc()}")
            return None

    def register_machine(self, machine_id, static_data):
        """Register a machine in the database."""
        try:
            machine_record = {
                'machine_id': machine_id,
                'hostname': static_data.get('os', {}).get('hostname', 'Unknown'),
                'os_name': static_data.get('os', {}).get('nom', 'Unknown'),
                'last_seen': datetime.now(),
                'status': 'active'
            }
            existing = self.machine_ids_collection.find_one({'machine_id': machine_id})
            if existing:
                self.machine_ids_collection.update_one(
                    {'machine_id': machine_id},
                    {'$set': machine_record}
                )
            else:
                machine_record['first_seen'] = datetime.now()
                self.machine_ids_collection.insert_one(machine_record)
            logging.info(f"Machine {machine_id} registered")
            return True
        except Exception as e:
            logging.error(f"Error registering machine: {e}\n{traceback.format_exc()}")
            return False

    def save_static_data(self, machine_id, data):
        """Save static data to MongoDB."""
        try:
            static_doc = {
                'machine_id': machine_id,
                'timestamp': datetime.now(),
                'data_received': data.get('timestamp', ''),
                'os': data.get('os', {}),
                'type_machine': data.get('type_machine', 0),
                'cpu': data.get('cpu', {}),
                'memoire': data.get('memoire', {}),
                'disque': data.get('disque', {}),
                'adresse_mac': data.get('adresse_mac', ''),
                'resolution_ecran': data.get('resolution_ecran', ''),
                'gpu': data.get('gpu', {}),
                'interfaces_reseau': data.get('interfaces_reseau', []),
                'bios_carte_mere': data.get('bios_carte_mere', {}),
                'utilisateurs_connectes': data.get('utilisateurs_connectes', []),
                'partitions_disque': data.get('partitions_disque', []),
                'peripheriques_usb': data.get('peripheriques_usb', []),
                'battery_initial': data.get('battery_initial', {}),
                'heure_demarrage_systeme': data.get('heure_demarrage_systeme', '')
            }
            self.static_collection.update_one(
                {'machine_id': machine_id},
                {'$set': static_doc},
                upsert=True
            )
            logging.info(f"Static data saved for {machine_id}")
            return True
        except Exception as e:
            logging.error(f"Error saving static data: {e}\n{traceback.format_exc()}")
            return False

    def save_variable_data(self, machine_id, data):
        """Save variable data to MongoDB."""
        try:
            variable_doc = {
                'machine_id': machine_id,
                'timestamp': datetime.now(),
                'data_received': data.get('timestamp', ''),
                'cpu': data.get('cpu', {}),
                'memoire': data.get('memoire', {}),
                'disque': data.get('disque', {}),
                'gpu_utilisation': data.get('gpu_utilisation', {}),
                'reseau': data.get('reseau', {}),
                'connexion_internet': data.get('connexion_internet', False),
                'nombre_processus': data.get('nombre_processus', 0),
                'battery': data.get('battery', {}),
                'uptime': data.get('uptime', ''),
                'seuil_atteint': data.get('seuil_atteint', {})
            }
            result = self.variable_collection.insert_one(variable_doc)
            self.machine_ids_collection.update_one(
                {'machine_id': machine_id},
                {'$set': {'last_seen': datetime.now()}}
            )
            logging.info(f"Variable data saved for {machine_id}, document ID: {result.inserted_id}")
            return True
        except Exception as e:
            logging.error(f"Error saving variable data: {e}\n{traceback.format_exc()}")
            return False

    def cleanup_old_data(self):
        """Remove old variable data from MongoDB."""
        try:
            cutoff = datetime.now() - timedelta(days=DATA_RETENTION_DAYS)
            result = self.variable_collection.delete_many({'timestamp': {'$lt': cutoff}})
            logging.info(f"Deleted {result.deleted_count} variable data documents older than {cutoff}")
        except Exception as e:
            logging.error(f"Error cleaning up old data: \n {traceback.format_exc()}")

    def process_data(self, data, filename, known_machine_id=None):
        """Process data from a JSON file, using known_machine_id if available."""
        try:
            if not data:
                logging.error(f"Empty data in {filename}")
                return None
            if 'os' in data:
                StaticData(**data)
                logging.info(f"Processing static data from {filename}")
                machine_id = self.generate_machine_id(data)
                if not machine_id or not self.register_machine(machine_id, data):
                    logging.error(f"Failed to register machine for {filename}")
                    return None
                if not self.save_static_data(machine_id, data):
                    logging.error(f"Failed to save static data for {filename}")
                    return None
                return machine_id
            else:
                # Treat as variable data, use known_machine_id if provided
                machine_id = known_machine_id
                if not machine_id:
                    logging.error(f"No machine_id available for variable data in {filename}")
                    return None
                logging.info(f"Processing variable data for {machine_id} from {filename}")
                if not self.machine_ids_collection.find_one({'machine_id': machine_id}):
                    logging.error(f"Machine ID {machine_id} not found in database for {filename}")
                    return None
                if not self.save_variable_data(machine_id, data):
                    logging.error(f"Failed to save variable data for {filename}")
                    return None
                return machine_id
        except ValidationError as e:
            logging.error(f"Invalid data in {filename}: {e}\n{traceback.format_exc()}")
            return None
        except Exception as e:
            logging.error(f"Error processing {filename}: {e}\n{traceback.format_exc()}")
            return None

    def find_data_directory(self, temp_dir):
        """Find the data directory in the unzipped folder."""
        data_dir = os.path.join(temp_dir, 'data')
        if os.path.exists(data_dir) and os.path.isdir(data_dir):
            return data_dir
        subdirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
        if len(subdirs) == 1:
            data_dir = os.path.join(temp_dir, subdirs[0], 'data')
            if os.path.exists(data_dir) and os.path.isdir(data_dir):
                return data_dir
        return None

    def find_machine_id_file(self, temp_dir):
        """Find the machine_id.txt file in the unzipped folder."""
        machine_id_file = os.path.join(temp_dir, 'machine_id.txt')
        if os.path.exists(machine_id_file):
            return machine_id_file
        subdirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
        if len(subdirs) == 1:
            machine_id_file = os.path.join(temp_dir, subdirs[0], 'machine_id.txt')
            if os.path.exists(machine_id_file):
                return machine_id_file
        return None

    def is_valid_json_file(self, file_path):
        """Check if a .json.gz file is valid and non-empty."""
        try:
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    logging.warning(f"File {file_path} is empty")
                    return False
                json.loads(content)  # Try parsing to ensure valid JSON
                return True
        except (gzip.BadGzipFile, json.JSONDecodeError) as e:
            logging.warning(f"File {file_path} is invalid or corrupted: {e}")
            return False
        except Exception as e:
            logging.error(f"Error checking {file_path}: {e}\n{traceback.format_exc()}")
            return False

    def process_zipped_folder(self, zip_path):
        """Process a zipped folder containing system-monitor data."""
        try:
            # Create a temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                logging.info(f"Extracting zip file {zip_path} to {temp_dir}")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)

                # Find machine_id.txt
                machine_id_file = self.find_machine_id_file(temp_dir)
                if machine_id_file:
                    with open(machine_id_file, 'r') as f:
                        self.machine_id = f.read().strip()
                    logging.info(f"Found machine ID: {self.machine_id}")

                # Find data directory
                data_dir = self.find_data_directory(temp_dir)
                if not data_dir:
                    logging.error(f"No data directory found in {zip_path}")
                    return False

                # Process data files
                json_files = sorted([f for f in os.listdir(data_dir) if f.endswith('.json.gz')])
                if not json_files:
                    logging.error(f"No .json.gz files found in {data_dir}")
                    return False

                # Prioritize static data (1.json.gz) if machine_id is not provided
                if not self.machine_id and '1.json.gz' in json_files:
                    json_files = ['1.json.gz'] + [f for f in json_files if f != '1.json.gz']

                for json_file in json_files:
                    file_path = os.path.join(data_dir, json_file)
                    # Check if file is valid before processing
                    if not self.is_valid_json_file(file_path):
                        logging.error(f"Skipping {json_file} due to invalid or empty content")
                        continue
                    try:
                        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                            file_data = json.load(f)
                        
                        # Process the data, passing the known machine_id
                        processed_machine_id = self.process_data(file_data, json_file, self.machine_id)
                        if processed_machine_id:
                            self.machine_id = processed_machine_id
                            logging.info(f"Successfully processed {json_file} for machine {self.machine_id}")
                        else:
                            logging.error(f"Failed to process {json_file}")
                    except Exception as e:
                        logging.error(f"Error processing {file_path}: {e}\n{traceback.format_exc()}")
                        continue  # Continue processing other files

                return True
        except Exception as e:
            logging.error(f"Error processing zip file {zip_path}: {e}\n{traceback.format_exc()}")
            return False

def main():
    """Main function to process a zipped folder."""
    import argparse
    parser = argparse.ArgumentParser(description="Process a zipped system-monitor folder and save data to MongoDB.")
    parser.add_argument('zip_path', help="Path to the zipped system-monitor folder")
    args = parser.parse_args()

    if not os.path.exists(args.zip_path):
        logging.error(f"Zip file {args.zip_path} does not exist")
        return

    processor = ZipDataProcessor()
    success = processor.process_zipped_folder(args.zip_path)
    if success:
        logging.info("Successfully processed all data from the zipped folder")
    else:
        logging.error("Failed to process the zipped folder")

if __name__ == "__main__":
    main()
