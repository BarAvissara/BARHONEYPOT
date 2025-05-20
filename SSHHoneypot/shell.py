import logging

from honeypot import *
import json
import os
from attacks import *

FAKE_FS_FILE = "fake_files.json"
DEFAULT_FS = {
    "home": {
        "user": {
            "fakefile.txt": "This is fake content.",
            "passwords.txt": "admin:12345\nroot:toor",
        },
        "supersecret": {
            "realpasswords.txt": "qwerty12345"
        }
    }
}


if os.path.exists(FAKE_FS_FILE):
    with open(FAKE_FS_FILE, "r") as f:
        try:
            fake_files = json.load(f)
        except json.JSONDecodeError:
            fake_files = DEFAULT_FS
else:
    fake_files = DEFAULT_FS
def save_fake_files():
    """Save the fake filesystem to JSON."""
    with open(FAKE_FS_FILE, "w") as f:
        json.dump(fake_files, f, indent=4)

def reset_fake_files():
    #resets file system
    global fake_files
    fake_files = DEFAULT_FS  # resets memory
    save_fake_files()  # saves
    logging.info("The system has been reset")
    return "Filesystem reset to default."

current_path = ["home", "user"]
def handle_shell(channel):
    channel.send("Welcome to Ubuntu 20.04.3 LTS (GNU/Linux 5.4.0-91-generic x86_64)\n")
    channel.send("Last login: Mon Oct 10 12:34:56 2022 from 192.168.1.100\n")
    channel.send("Type 'exit' to disconnect.\n")

    while True:
        channel.send(" ")
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
        elif command == 'whoami':
            channel.send("fakeuser\n")
        elif command == 'pwd':
            channel.send(f"{'/'.join(current_path)}\n")
        elif command.startswith('cd'):
            _, *args = command.split()
            if args:
                response = handle_cd(args[0])
                channel.send(response + "\n")
            else:
                channel.send("cd: Missing argument\n")
        elif command.startswith("echo"):
            response = handle_echo(command[5:].strip())
            channel.send(response + "\n")

        elif command.startswith("touch"):
            _, filename = command.split(maxsplit=1)
            response = handle_touch(filename)
            channel.send(response + "\n")

        elif command.startswith("rm"):
            _, filename = command.split(maxsplit=1)
            response = handle_rm(filename)
            channel.send(response + "\n")
        elif command == "resetfs":
            response = reset_fake_files()
            channel.send(response + "\n")
        elif command.startswith('sudo'):
            #troll for using admin command
            channel.send("[sudo] password for fakeuser: ")
            fake_password = channel.recv(1024).decode('utf-8').strip()
            logging.info(f"sudo password attempt: {fake_password}")
            if fake_password == "toor":  # troll by making them feel like they did something
                channel.send("Sorry, user fakeuser is not allowed to execute as root.\n")
            else:
                channel.send("Incorrect password\n")


        else:
            channel.send(f"{command}: command not found\n")
        detect_reverse_shell(command,channel)

    channel.close()

def handle_ls(path="."):
        global current_path  # global directory of path
        target_dir = fake_files

        # find current directory
        for part in current_path:
            target_dir = target_dir.get(part, {})

        # check if user provided a path
        if path != ".":
            parts = path.strip("/").split("/")
            for part in parts:
                if part in target_dir and isinstance(target_dir[part], dict):
                    target_dir = target_dir[part]
                else:
                    return f"{path}: Not a directory or does not exist"

        # return content of the directory
        return "\n".join(target_dir.keys()) if isinstance(target_dir, dict) else f"{path}: Not a directory"

def handle_cat(filename):
        global current_path
        target_dir = fake_files
        for part in current_path:
            target_dir = target_dir.get(part, {})

        if filename in target_dir and isinstance(target_dir[filename], str):
            return target_dir[filename]

        return "File not found"

def handle_cd(path):
        global current_path
        if path == "..":
            if len(current_path) > 1:
                current_path.pop()  # move back a directory
            return ""

        parts = path.strip("/").split("/")
        temp_dir = fake_files
        for part in current_path:
            temp_dir = temp_dir.get(part, {})

        for part in parts:
            if part in temp_dir and isinstance(temp_dir[part], dict):
                current_path.append(part)
                temp_dir = temp_dir[part]
            else:
                return f"cd: {path}: No such file or directory"

        return ""

def handle_touch(filename, content="", append=False):
    global current_path
    target_dir = fake_files

    for part in current_path:
        target_dir = target_dir.get(part, {})

    if filename in target_dir:
        if append and isinstance(target_dir[filename], str):  # append if the file exists
            target_dir[filename] += "\n" + content
            save_fake_files()
            return f"Appended to {filename}"
        else:
            target_dir[filename] = content  # else overwrite the file
            save_fake_files()
            return f"Overwritten {filename}"
    else:
        target_dir[filename] = content  # else create new file
        save_fake_files()
        return f"Created {filename}"

def handle_rm(filename):
    global current_path
    target_dir = fake_files

    for part in current_path:
        target_dir = target_dir.get(part, {})

    if filename in target_dir:
        del target_dir[filename]
        save_fake_files()
        return f"Deleted {filename}"
    return "File not found"

def handle_echo(command):
    parts = command.split(">", 1)  # check for > or >>
    message = parts[0].strip()

    append_mode = False
    filename = None

    if len(parts) == 2:
        redirection = parts[1].strip()
        if redirection.startswith(">"):  # check for >>
            append_mode = True
            filename = redirection[1:].strip()
        else:
            filename = redirection.strip()

        return handle_touch(filename, message, append_mode)  # write in file

    return message  #if no redirection just write the msg
