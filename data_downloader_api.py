from flask import Flask, request, jsonify
import subprocess
import sys
from datetime import datetime, timedelta
import logging
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

def run_and_log_subprocess(command):
    """
    Executes a command in a subprocess and logs its output.
    """
    logging.info(f"Subprocess started for command: {' '.join(command)}")
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()

        if stdout:
            logging.info(f"Subprocess stdout:\n{stdout}")
        if stderr:
            logging.error(f"Subprocess stderr:\n{stderr}")
        
        logging.info("Subprocess finished.")

    except Exception as e:
        logging.error(f"Subprocess execution failed: {e}")


@app.route('/download', methods=['POST'])
def download_data():
    """
    An API endpoint to trigger the download of historical market data.
    Expects a JSON payload with 'symbol' and 'timeframe'.
    """
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        timeframe = data.get('timeframe')

        if not symbol or not timeframe:
            return jsonify({"status": "error", "message": "'symbol' and 'timeframe' are required."}), 400

        logging.info(f"Received request to download data for {symbol} ({timeframe}).")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        end_date_str = end_date.strftime('%Y-%m-%d')
        start_date_str = start_date.strftime('%Y-%m-%d')

        command = [
            sys.executable,
            'historical_data_importer.py',
            symbol,
            timeframe,
            start_date_str,
            end_date_str
        ]

        # Run the subprocess in a background thread to avoid blocking the API response
        thread = threading.Thread(target=run_and_log_subprocess, args=(command,))
        thread.daemon = True
        thread.start()
        
        return jsonify({"status": "success", "message": f"Data download process for {symbol} ({timeframe}) started in background."}), 202

    except Exception as e:
        logging.error(f"An unexpected error occurred when starting the download process: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9091, debug=False) # Turn off debug mode for cleaner logs with threading