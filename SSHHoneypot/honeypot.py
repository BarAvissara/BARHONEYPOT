import socket
import paramiko
import logging
from concurrent.futures import ThreadPoolExecutor
import threading
import sqlite3
from attacks import *
from shell import *
conn = sqlite3.connect('honeypot.db')
cursor = conn.cursor()
import json
from pathlib import Path
# create table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    password TEXT NOT NULL
)
''')

cursor.execute("INSERT INTO users (username, password) VALUES ('admin', 'password123')")
cursor.execute("INSERT INTO users (username, password) VALUES ('guest', 'guestpass')")
cursor.execute("INSERT INTO users (username, password) VALUES ('user1', 'userpass')")

conn.commit()
conn.close()

conn = sqlite3.connect('honeypot.db')
cursor = conn.cursor()


logging.basicConfig(filename='honeypot.log', level=logging.INFO, format='%(asctime)s - %(message)s')


class SSHServer(paramiko.ServerInterface):
    def __init__(self,client_ip):
        self.event = threading.Event()
        self.__client_ip = client_ip
        super().__init__()
        print("SSHServer initialized")

    def check_auth_password(self, username, password):
        logging.info(f"Login attempt - Username: {username}, Password: {password}")


        if blacklist_manager.contains(self.__client_ip):  # blacklist check
            logging.warning(f"BLOCKED: {self.__client_ip} (blacklisted)")
            return paramiko.AUTH_FAILED
        conn = sqlite3.connect('honeypot.db')
        cursor = conn.cursor()
        # sql check
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        with open("SQLQueries.log", "a") as log:
            log.write(f"Attempted Query: {query}\n")
        cursor.execute(query)
        user = cursor.fetchone()


        if user:
            detect_sql_injection(username,client_addr[0],query)
            detect_sql_injection(password,client_addr[0],query)
            return paramiko.AUTH_SUCCESSFUL
        detect_brute_force(username, client_addr[0])
        return paramiko.AUTH_FAILED



    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

class BlacklistManager:
    def __init__(self, file_path="blacklist.json"):
        self.file_path = Path(file_path)
        self.blacklisted_ips = set()
        self.load()

    def load(self):
        if self.file_path.exists():
            with open(self.file_path, 'r') as f:
                self.blacklisted_ips = set(json.load(f))

    def save(self):
        with open(self.file_path, 'w') as f:
            json.dump(list(self.blacklisted_ips), f)

    def add(self, ip):
        self.blacklisted_ips.add(ip)
        self.save()

    def remove(self, ip):
        self.blacklisted_ips.discard(ip)
        self.save()

    def contains(self, ip):
        return ip in self.blacklisted_ips

# global variant
blacklist_manager = BlacklistManager()


def handle_connection(client,client_adrr):
    start_time = time.time()
    try:
        transport = paramiko.Transport(client)
        server_key = paramiko.RSAKey.from_private_key_file('key')
        transport.add_server_key(server_key)
        ssh = SSHServer(client_adrr[0])
        transport.start_server(server=ssh)

        channel = transport.accept(20)
        if channel is not None:
            handle_shell(channel)
    except Exception as e:
        logging.error(f"Connection handling error: {e}")
    finally:
        duration = time.time() - start_time
        logging.info(f"Session ended - IP: {client_addr[0]}, Duration: {duration:.2f}s")
        client.close()



def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    port=22
    server_sock.bind(('', port))
    server_sock.listen(100)
    logging.info(f"SSH Honeypot listening on port {port}")

    with ThreadPoolExecutor(max_workers=10) as executor:
        while True:
            global client_addr
            client_sock, client_addr = server_sock.accept()
            logging.info(f"New connection from {client_addr[0]}:{client_addr[1]}")
            executor.submit(handle_connection, client_sock,client_addr)


if __name__ == "__main__":
    main()