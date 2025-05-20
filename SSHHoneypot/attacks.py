from collections import defaultdict
import time
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

failed_attempts = defaultdict(list)
MAX_FAILED_ATTEMPTS = 10  # max faile attempts before trigger
TIME_FRAME = 20  # max time before trigger

def detect_brute_force(username, client_ip):
    current_time = time.time()

    # add the current time to the list
    failed_attempts[username].append(current_time)
    failed_attempts[client_ip].append(current_time)

    # remove attempts that passed the time frame
    failed_attempts[username] = [t for t in failed_attempts[username] if current_time - t < TIME_FRAME]
    failed_attempts[client_ip] = [t for t in failed_attempts[client_ip] if current_time - t < TIME_FRAME]

    # check if number of attempts> max failed attempts
    if len(failed_attempts[username]) >= MAX_FAILED_ATTEMPTS:
        logging.warning(f"Brute force detected for username: {username} (Attempts: {len(failed_attempts[username])})")
        send_email_alert(
            "Brute Force Attack Detected (Username)",
            f"Brute force attack detected for username: {username} from IP: {client_ip}. Attempts: {len(failed_attempts[username])}"
        )
    if len(failed_attempts[client_ip]) >= MAX_FAILED_ATTEMPTS:
        logging.warning(f"Brute force detected from IP: {client_ip} (Attempts: {len(failed_attempts[client_ip])})")
        send_email_alert(
            "Brute Force Attack Detected (IP)",
            f"Brute force attack detected from IP: {client_ip}. Attempts: {len(failed_attempts[client_ip])}"
        )

# sql input ' OR '1'='1
def detect_sql_injection(input,client_ip,query):
    suspicious_patterns = ["'", '"', "--", ";", " OR ", " AND ", " UNION ", " SELECT ", " DROP ", " INSERT ",  " DELETE ", " UPDATE "]
    if any(pattern in input.upper() for pattern in suspicious_patterns):
        logging.warning(f"Possible SQL Injection Attempt: {input}\n")
        send_email_alert(
            "SQL Injection detected (IP)",
            f"SQL Injection attack detected from IP: {client_ip}. Query: {query}"
        )

def detect_reverse_shell(command,channel):
    flag=False
    type = ""
    if "nc " in command or "netcat " in command or "bash -i" in command or "python -c" in command:
        channel.send("Connection refused: Operation not permitted\n")
        logging.warning(f"Attempted reverse shell: {command}")
        type = "normal reverse shell"
    elif command in ["sh", "bash", "/bin/sh", "/bin/bash"]:
        channel.send("Permission denied\n")
        logging.warning(f"Attempted shell spawn: {command}")
        type = "Shell spawn"
    elif "import socket" in command and "subprocess.call" in command:
        channel.send("Error: No module named socket\n")
        logging.warning("Python reverse shell attempt detected")
        type = "Python reverse shell"
    else:
        flag=True
    if flag is False:
            send_email_alert(
            "Reverse shell attempt detected",
            f"Reverse shell detected. Query: {type}"
        )


def send_email_alert(subject, body):
    sender_email = "barsshhoneypot@gmail.com"
    receiver_email = "barsshhoneypot@example.com"
    password = "jkaz cwel hzhg cmla"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        # connect to STMP
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        print("Email alert sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")