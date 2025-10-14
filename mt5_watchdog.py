import time
import logging
import subprocess
import pika
import psutil
import os
import json

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SCRIPT_NAME = "mt5_bridge.py"
# This assumes the watchdog is run from the project root, like the bridge.
SCRIPT_PATH = os.path.join(os.path.dirname(__file__), SCRIPT_NAME)

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
HEARTBEAT_QUEUE = 'mt5_bridge_heartbeat'
HEARTBEAT_TIMEOUT = 60  # seconds. If no heartbeat is received in this time, restart the bridge.
CHECK_INTERVAL = 10 # seconds. How often the watchdog checks the status.

def find_script_pid(script_name):
    """Find the PID of the running mt5_bridge.py script."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if the process is a python process and if the script name is in its command line
            if 'python' in proc.info['name'].lower() and len(proc.info['cmdline']) > 1:
                if script_name in proc.info['cmdline'][1]:
                    logging.info(f"Found existing bridge process with PID: {proc.info['pid']}")
                    return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def restart_script(symbols):
    """Restarts the mt5_bridge.py script with given symbols."""
    if not symbols:
        logging.error("Cannot restart script: no symbols provided.")
        return None
    
    command = ["python", SCRIPT_PATH] + symbols
    logging.info(f"Attempting to restart script with command: {' '.join(command)}")
    try:
        # Using Popen to run the script in a new process without blocking
        process = subprocess.Popen(command)
        logging.info(f"Successfully started new bridge process with PID: {process.pid}")
        return process.pid
    except Exception as e:
        logging.error(f"Failed to restart script: {e}")
        return None

class Watchdog:
    def __init__(self, symbols):
        self.symbols = symbols
        self.bridge_pid = None
        self.last_heartbeat_time = time.time()
        self.connection = None
        self.channel = None

    def connect_to_rabbitmq(self):
        """Connects to RabbitMQ and declares the heartbeat queue."""
        try:
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            self.channel = self.connection.channel()
            # Purge the queue on startup to clear any old heartbeats
            self.channel.queue_declare(queue=HEARTBEAT_QUEUE, durable=False)
            self.channel.queue_purge(queue=HEARTBEAT_QUEUE)
            logging.info("Watchdog connected to RabbitMQ and purged heartbeat queue.")
            return True
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"Watchdog failed to connect to RabbitMQ: {e}")
            return False

    def check_heartbeat(self):
        """Check for a new heartbeat message in the queue."""
        try:
            # Try to get a message without blocking
            method_frame, header_frame, body = self.channel.basic_get(HEARTBEAT_QUEUE, auto_ack=True)
            if method_frame:
                self.last_heartbeat_time = time.time()
                heartbeat_data = json.loads(body.decode())
                # Update PID from heartbeat message
                self.bridge_pid = heartbeat_data.get('pid')
                logging.info(f"Heartbeat received. Bridge PID: {self.bridge_pid}")
        except pika.exceptions.AMQPConnectionError:
            logging.warning("RabbitMQ connection lost while checking heartbeat. Will attempt to reconnect.")
            self.connect_to_rabbitmq() # Attempt to reconnect
        except Exception as e:
            logging.error(f"Error checking heartbeat: {e}")

    def run(self):
        """Main loop for the watchdog."""
        if not self.connect_to_rabbitmq():
            logging.error("Cannot start watchdog without RabbitMQ connection. Exiting.")
            return

        # Initial check for the script
        self.bridge_pid = find_script_pid(SCRIPT_NAME)
        if not self.bridge_pid:
            logging.warning("Bridge script not running at startup. Attempting to start it.")
            self.bridge_pid = restart_script(self.symbols)
            self.last_heartbeat_time = time.time() # Reset timer after restart

        while True:
            self.check_heartbeat()

            is_alive = self.bridge_pid is not None and psutil.pid_exists(self.bridge_pid)
            heartbeat_ok = (time.time() - self.last_heartbeat_time) < HEARTBEAT_TIMEOUT

            if is_alive and heartbeat_ok:
                logging.info("Bridge is alive and heartbeat is OK.")
            else:
                if not is_alive:
                    logging.warning("Bridge process is not running!")
                if not heartbeat_ok:
                    logging.warning("Heartbeat timeout! No heartbeat received recently.")
                
                # Kill the old process if it's still running (zombie)
                if is_alive:
                    try:
                        p = psutil.Process(self.bridge_pid)
                        p.kill()
                        logging.info(f"Killed zombie bridge process {self.bridge_pid}.")
                    except psutil.NoSuchProcess:
                        pass # Already gone
                
                # Restart the script
                self.bridge_pid = restart_script(self.symbols)
                self.last_heartbeat_time = time.time() # Reset timer

            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # The symbols must be provided to the watchdog so it knows how to restart the bridge
    # In a real scenario, these would be passed via command-line arguments
    # For this example, we'll hardcode them.
    # You would run this as: python mt5_watchdog.py EURUSD XAUUSD
    import sys
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <symbol1> <symbol2> ...")
        print(f"Example: python {sys.argv[0]} EURUSD XAUUSD")
        sys.exit(1)
    
    watchdog_symbols = sys.argv[1:]
    watchdog = Watchdog(symbols=watchdog_symbols)
    watchdog.run()
