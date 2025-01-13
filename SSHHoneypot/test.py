
import paramiko
import time

def ssh_client(server_ip, server_port, username, password):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        print(f"Connecting to {server_ip}:{server_port}...")
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
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    SERVER_IP = "127.0.0.1"
    SERVER_PORT = 12537
    USERNAME = input("Enter username: ")
    PASSWORD = input("Enter Password: ")

    ssh_client(SERVER_IP, SERVER_PORT, USERNAME, PASSWORD)