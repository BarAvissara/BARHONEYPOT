import paramiko
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import time


class SSHClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SSH Client")
        self.root.geometry("800x600")

        # connection variables
        self.client = None
        self.channel = None
        self.connected = False

        self.create_widgets()

    def create_widgets(self):
        # connection settings text
        conn_frame = tk.LabelFrame(self.root, text="Connection Settings", padx=5, pady=5)
        conn_frame.pack(fill=tk.X, padx=5, pady=5)

        # ip box
        tk.Label(conn_frame, text="Server IP:").grid(row=0, column=0, sticky="e")
        self.ip_entry = tk.Entry(conn_frame)
        self.ip_entry.grid(row=0, column=1, sticky="we")


        # port box
        tk.Label(conn_frame, text="Port:").grid(row=0, column=2, sticky="e")
        self.port_entry = tk.Entry(conn_frame, width=8)
        self.port_entry.grid(row=0, column=3)

        # username box
        tk.Label(conn_frame, text="Username:").grid(row=1, column=0, sticky="e")
        self.user_entry = tk.Entry(conn_frame)
        self.user_entry.grid(row=1, column=1, sticky="we")

        # password box
        tk.Label(conn_frame, text="Password:").grid(row=1, column=2, sticky="e")
        self.pass_entry = tk.Entry(conn_frame, show="*")
        self.pass_entry.grid(row=1, column=3, sticky="we")

        # connect button
        self.connect_btn = tk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=4, rowspan=2, padx=5, sticky="nswe")

        # console
        self.console = scrolledtext.ScrolledText(self.root, state='normal', wrap=tk.WORD)
        self.console.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.console.tag_config('command', foreground="blue")
        self.console.tag_config('output', foreground="black")

        # input box
        cmd_frame = tk.Frame(self.root)
        cmd_frame.pack(fill=tk.X, padx=5, pady=5)

        self.cmd_entry = tk.Entry(cmd_frame)
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.cmd_entry.bind("<Return>", self.send_command)

        tk.Button(cmd_frame, text="Send", command=self.send_command).pack(side=tk.RIGHT)

        # disables console editing
        self.console.bind("<Key>", lambda e: "break")

    def toggle_connection(self):
        if self.connected:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        server_ip = self.ip_entry.get()
        server_port = int(self.port_entry.get())
        username = self.user_entry.get()
        password = self.pass_entry.get()

        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self.print_to_console(f"Connecting to {server_ip}:{server_port}...\n", 'output')

            threading.Thread(
                target=self.establish_connection,
                args=(server_ip, server_port, username, password),
                daemon=True
            ).start()

        except Exception as e:
            self.print_to_console(f"Connection error: {str(e)}\n", 'output')

    def establish_connection(self, server_ip, server_port, username, password):
        try:
            self.client.connect(server_ip, port=server_port,
                                username=username, password=password)
            self.channel = self.client.invoke_shell()
            self.connected = True

            self.root.after(0, self.update_connect_ui, True)
            self.print_to_console("Connected! Enter commands below.\n", 'output')

            threading.Thread(target=self.receive_output, daemon=True).start()

        except Exception as e:
            self.print_to_console(f"Connection failed: {str(e)}\n", 'output')
            self.client.close()

    def disconnect(self):
        if self.connected:
            if self.channel:
                self.channel.close()
            if self.client:
                self.client.close()
            self.connected = False
            self.update_connect_ui(False)
            self.print_to_console("Disconnected.\n", 'output')

    def update_connect_ui(self, connected):
        state = 'disabled' if connected else 'normal'
        self.connect_btn.config(text="Disconnect" if connected else "Connect",
                                bg="lightcoral" if connected else "lightgreen")
        self.ip_entry.config(state=state)
        self.port_entry.config(state=state)
        self.user_entry.config(state=state)
        self.pass_entry.config(state=state)

    def receive_output(self):
        while self.connected:
            try:
                if self.channel.recv_ready():
                    output = self.channel.recv(1024).decode('utf-8')
                    self.print_to_console(output, 'output')
                time.sleep(0.1)
            except:
                if self.connected:  # print connection lost if server crashed
                    self.print_to_console("\nConnection lost!\n", 'output')
                self.root.after(0, self.disconnect)
                break

    def send_command(self, event=None):
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect first!")
            return

        command = self.cmd_entry.get()
        self.cmd_entry.delete(0, tk.END)

        if command.lower() == 'exit':
            self.disconnect()
            return

        try:
            # display command sent
            self.print_to_console(f"$ {command}\n", 'command')
            self.channel.send(command + '\n')
        except Exception as e:
            self.print_to_console(f"Error sending command: {str(e)}\n", 'output')

    def print_to_console(self, message, tag='output'):
        self.console.config(state='normal')
        self.console.insert(tk.END, message, tag)
        self.console.see(tk.END)
        self.console.config(state='disabled')

    def on_closing(self):
        if self.connected:
            self.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = SSHClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()