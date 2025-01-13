import socket
import paramiko
import logging
from concurrent.futures import ThreadPoolExecutor
import threading


logging.basicConfig(filename='honeypot.log', level=logging.INFO, format='%(asctime)s - %(message)s')
fake_files = {
    "home": {
        "user": {
            "fakefile.txt": "This is fake content.",
            "passwords.txt": "admin:12345\nroot:toor",
        }
        ,"supersecret":
            {
            "realpasswords.txt":"qwerty12345"
        }
    }
}

class SSHServer(paramiko.ServerInterface):
    def __init__(self):
        self.event = threading.Event()
        super().__init__()
        print("SSHServer initialized")

    def check_auth_password(self, username, password):
        logging.info(f"Login attempt - Username: {username}, Password: {password}")
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

def handle_shell(channel):
    channel.send("Welcome to the very important secret server!\n")
    channel.send("Type 'exit' to disconnect.\n")

    while True:
        channel.send("$ ")
        command = channel.recv(1024).decode('utf-8').strip()
        logging.info(f"Command received: {command}")

        if command.lower() == 'exit':
            channel.send("Goodbye!\n")
            break
        elif command.startswith('ls'):
            path = command[3:].strip() or "."
            response = handle_ls(path)
            channel.send(response + "\n")
        elif command.startswith('cat'):
            _, *args = command.split()
            if args:
                response = handle_cat(args[0])
                channel.send(response + "\n")
            else:
                response = "cat: Missing file operand"
                channel.send(response + "\n")
            channel.send("$ ")  # Send prompt immediately after output
        elif command == 'whoami':
            channel.send("fakeuser\n")
            channel.send("$ ")
        else:
            channel.send(f"{command}: command not found\n")
            channel.send("$ ")  # Send prompt immediately after output

    channel.close()


def handle_connection(client):
    try:
        transport = paramiko.Transport(client)
        server_key = paramiko.RSAKey.from_private_key_file('key')
        transport.add_server_key(server_key)
        ssh = SSHServer()
        transport.start_server(server=ssh)

        channel = transport.accept(20)  # Timeout of 20 seconds for client connection
        if channel is not None:
            handle_shell(channel)
    except Exception as e:
        logging.error(f"Connection handling error: {e}")
    finally:
        client.close()


def handle_ls(path):
    path = path.strip() or '.'
    parts = path.strip("/").split("/")
    current_dir = fake_files
    for part in parts:
        if part in current_dir and isinstance(current_dir[part], dict):
            current_dir = current_dir[part]
        else:
            return f"{path}: Not a directory or does not exist"

    return "\n".join(current_dir.keys()) if isinstance(current_dir, dict) else f"{path}: Not a directory"

def handle_cat(path):
    parts = path.strip("/").split("/")
    current_dir = fake_files
    for part in parts[:-1]:
        current_dir = current_dir.get(part, {})
    return current_dir.get(parts[-1], "File not found")

def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(('', 12537))
    server_sock.listen(100)
    logging.info("SSH Honeypot listening on port 12537")

    with ThreadPoolExecutor(max_workers=10) as executor:
        while True:
            client_sock, client_addr = server_sock.accept()
            logging.info(f"New connection from {client_addr[0]}:{client_addr[1]}")
            executor.submit(handle_connection, client_sock)


if __name__ == "__main__":
    main()