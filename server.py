#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import json
import hashlib
import threading
from datetime import datetime, timedelta
from pymongo import MongoClient
import logging
import traceback
from pydantic import BaseModel, ValidationError
from concurrent.futures import ThreadPoolExecutor
import signal
import sys

# Configuration
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 12345
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
DATABASE_NAME = 'machine_monitoring'
STATIC_COLLECTION = 'static_data'
VARIABLE_COLLECTION = 'variable_data'
MACHINE_IDS_COLLECTION = 'machine_ids'
DATA_RETENTION_DAYS = 30
MAX_CONCURRENT_CONNECTIONS = 50  # Maximum number of concurrent clients

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log'),
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

class MonitoringServer:
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
            logging.info("Connexion MongoDB établie")
            self.cleanup_old_data()
            self.active_connections = 0
            self.lock = threading.Lock()
        except Exception as e:
            logging.error(f"Erreur connexion MongoDB: {e}\n{traceback.format_exc()}")
            raise

    def generate_machine_id(self, static_data):
        """Génère un ID machine basé sur les caractéristiques statiques."""
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
            logging.error(f"Erreur génération ID machine: {e}\n{traceback.format_exc()}")
            return None

    def register_machine(self, machine_id, static_data):
        """Enregistre une machine dans la base."""
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
            logging.info(f"Machine {machine_id} enregistrée")
            return True
        except Exception as e:
            logging.error(f"Erreur enregistrement machine: {e}\n{traceback.format_exc()}")
            return False

    def save_static_data(self, machine_id, data):
        """Sauvegarde les données statiques."""
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
            logging.info(f"Données statiques sauvegardées pour {machine_id}")
            return True
        except Exception as e:
            logging.error(f"Erreur sauvegarde statique: {e}\n{traceback.format_exc()}")
            return False

    def save_variable_data(self, machine_id, data):
        """Sauvegarde les données variables."""
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
            logging.info(f"Données variables sauvegardées pour {machine_id}, ID document: {result.inserted_id}")
            return True
        except Exception as e:
            logging.error(f"Erreur sauvegarde variable: {e}\n{traceback.format_exc()}")
            return False

    def cleanup_old_data(self):
        """Supprime les données variables anciennes."""
        try:
            cutoff = datetime.now() - timedelta(days=DATA_RETENTION_DAYS)
            result = self.variable_collection.delete_many({'timestamp': {'$lt': cutoff}})
            logging.info(f"Données variables antérieures à {cutoff} supprimées, {result.deleted_count} documents")
        except Exception as e:
            logging.error(f"Erreur nettoyage données: {e}\n{traceback.format_exc()}")

    def process_data(self, data, client_address):
        """Traite les données reçues."""
        try:
            if not data.get('version') == "1.0":
                return {'status': 'error', 'message': 'Invalid data version'}
            content = data.get('content')
            if 'os' in content:
                StaticData(**content)
                logging.info(f"Données statiques reçues de {client_address}")
                machine_id = self.generate_machine_id(content)
                if not machine_id or not self.register_machine(machine_id, content):
                    return {'status': 'error', 'message': 'Failed to register machine'}
                if not self.save_static_data(machine_id, content):
                    return {'status': 'error', 'message': 'Failed to save static data'}
                return {'status': 'success', 'machine_id': machine_id, 'message': 'Static data registered'}
            elif 'machine_id' in data:
                machine_id = data.get('machine_id')
                logging.info(f"Données variables reçues pour {machine_id}")
                if not self.machine_ids_collection.find_one({'machine_id': machine_id}):
                    return {'status': 'error', 'message': 'RESEND_STATIC_DATA'}
                if not self.save_variable_data(machine_id, content):
                    return {'status': 'error', 'message': 'Failed to save variable data'}
                return {'status': 'success', 'message': 'Variable data saved'}
            else:
                return {'status': 'error', 'message': 'Invalid data format'}
        except ValidationError as e:
            logging.error(f"Données invalides de {client_address}: {e}\n{traceback.format_exc()}")
            return {'status': 'error', 'message': 'Invalid data format'}
        except Exception as e:
            logging.error(f"Erreur traitement données: {e}\n{traceback.format_exc()}")
            return {'status': 'error', 'message': str(e)}

    def handle_client(self, client_socket, client_address):
        """Gère un client, recevant plusieurs fichiers dans une connexion."""
        try:
            with self.lock:
                self.active_connections += 1
                if self.active_connections > MAX_CONCURRENT_CONNECTIONS:
                    logging.warning(f"Limite de connexions atteinte, rejet de {client_address}")
                    client_socket.send(json.dumps({'status': 'error', 'message': 'Too many connections'}).encode('utf-8'))
                    return
                logging.info(f"Connexion de {client_address}, connexions actives: {self.active_connections}")

            data = b""
            while True:
                packet = client_socket.recv(4096)
                if not packet:
                    logging.info(f"Client {client_address} a fermé la connexion")
                    break
                data += packet
                # Process complete JSON messages (delimited by newline)
                while b'\n' in data:
                    message, _, data = data.partition(b'\n')
                    try:
                        json_data = json.loads(message.decode('utf-8'))
                        response = self.process_data(json_data, client_address)
                        client_socket.sendall(json.dumps(response).encode('utf-8') + b'\n')
                    except json.JSONDecodeError as e:
                        logging.error(f"JSON invalide de {client_address}: {e}\n{traceback.format_exc()}")
                        client_socket.sendall(json.dumps({'status': 'error', 'message': 'Invalid JSON'}).encode('utf-8') + b'\n')
                    except Exception as e:
                        logging.error(f"Erreur traitement message de {client_address}: {e}\n{traceback.format_exc()}")
                        client_socket.sendall(json.dumps({'status': 'error', 'message': str(e)}).encode('utf-8') + b'\n')
        except (ConnectionResetError, BrokenPipeError) as e:
            logging.error(f"Erreur réseau client {client_address}: {e}\n{traceback.format_exc()}")
        except Exception as e:
            logging.error(f"Erreur client {client_address}: {e}\n{traceback.format_exc()}")
        finally:
            try:
                client_socket.close()
            except:
                pass
            with self.lock:
                self.active_connections -= 1
            logging.info(f"Connexion fermée avec {client_address}, connexions actives: {self.active_connections}")

    def start_server(self):
        """Démarre le serveur avec un pool de threads."""
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((SERVER_HOST, SERVER_PORT))
            server_socket.listen(MAX_CONCURRENT_CONNECTIONS)
            logging.info(f"Serveur démarré sur {SERVER_HOST}:{SERVER_PORT}, max connexions: {MAX_CONCURRENT_CONNECTIONS}")

            with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_CONNECTIONS) as executor:
                def shutdown_server(*args):
                    logging.info("Signal d'arrêt reçu, arrêt du serveur")
                    server_socket.close()
                    self.mongo_client.close()
                    sys.exit(0)

                signal.signal(signal.SIGINT, shutdown_server)
                signal.signal(signal.SIGTERM, shutdown_server)

                while True:
                    client_socket, client_address = server_socket.accept()
                    executor.submit(self.handle_client, client_socket, client_address)
        except Exception as e:
            logging.error(f"Erreur serveur: {e}\n{traceback.format_exc()}")
        finally:
            try:
                server_socket.close()
            except:
                pass
            self.mongo_client.close()
            logging.info("Serveur arrêté")

    def get_machine_stats(self):
        """Affiche les statistiques."""
        try:
            print(f"\n=== STATISTIQUES ===")
            print(f"Machines: {self.machine_ids_collection.count_documents({})}")
            print(f"Actives: {self.machine_ids_collection.count_documents({'status': 'active'})}")
            print(f"Statiques: {self.static_collection.count_documents({})}")
            print(f"Variables: {self.variable_collection.count_documents({})}")
            print(f"===================\n")
        except Exception as e:
            logging.error(f"Erreur statistiques: {e}\n{traceback.format_exc()}")

def main():
    """Fonction principale."""
    try:
        server = MonitoringServer()
        server.get_machine_stats()
        server.start_server()
    except Exception as e:
        logging.error(f"Erreur fatale: {e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()