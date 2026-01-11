from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import threading
import json
from publisher import Publisher
from consumer import Consumer
from influx_connector import InfluxDBConnector
from postgresql_client import PostgreSQLConnector
from economic_calendar import get_economic_events

from config import get_config, CriticalConfigurationError

app = Flask(__name__)

# Global dictionary to hold the latest market data for each symbol
latest_market_data = {}

# --- Securely Load Configuration ---
try:
    cfg = get_config()
    BROKER_HOST = cfg.BROKER_HOST
    BROKER_PORT = cfg.BROKER_PORT
    BROKER_USER = cfg.BROKER_USER
    BROKER_PASS = cfg.BROKER_PASS

    INFLUXDB_URL = cfg.INFLUXDB_URL
    INFLUXDB_TOKEN = cfg.INFLUXDB_TOKEN
    INFLUXDB_ORG = cfg.INFLUXDB_ORG
    INFLUXDB_BUCKET = cfg.INFLUXDB_BUCKET

    PG_DBNAME = cfg.PG_DBNAME
    PG_USER = cfg.PG_USER
    PG_PASSWORD = cfg.PG_PASSWORD
    PG_HOST = cfg.PG_HOST
    PG_PORT = cfg.PG_PORT

except CriticalConfigurationError as e:
    print(f"FATAL: Could not load configuration. Error: {e}")
    # In production, we might want to sys.exit(1) here
    pass



@app.route('/')
def index():
    return render_template('index.html')



@app.route('/status')
def status_page():
    
    status_info = {}

    # Check RabbitMQ connection
    try:
        publisher = Publisher(BROKER_HOST, BROKER_PORT, BROKER_USER, BROKER_PASS)
        publisher.connect()
        status_info['rabbitmq'] = "Connected"
        publisher.close()
    except Exception as e:
        status_info['rabbitmq'] = f"Connection failed"

    # Check InfluxDB connection
    try:
        influx_connector = InfluxDBConnector(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG, bucket=INFLUXDB_BUCKET)
        influx_connector.write_data(measurement="web_status_check", tags={"service": "web"}, fields={"status": 1})
        status_info['influxdb'] = "Connected"
        influx_connector.close()
    except Exception as e:
        status_info['influxdb'] = f"Connection failed"

    # Check PostgreSQL connection
    try:
        pg_connector = PostgreSQLConnector(
            dbname=PG_DBNAME,
            user=PG_USER,
            password=PG_PASSWORD,
            host=PG_HOST,
            port=PG_PORT
        )
        pg_connector.connect()
        if pg_connector.conn:
            status_info['postgresql'] = "Connected"
            pg_connector.close()
        else:
            status_info['postgresql'] = "Connection failed"
    except Exception as e:
        status_info['postgresql'] = f"Connection failed"
        
    return render_template('status.html', status=status_info)

@app.route('/api/status')
def api_status():

    status_info = {}

    # Check RabbitMQ connection
    try:
        publisher = Publisher(BROKER_HOST, BROKER_PORT, BROKER_USER, BROKER_PASS)
        publisher.connect()
        status_info['rabbitmq'] = "Connected"
        publisher.close()
    except Exception as e:
        status_info['rabbitmq'] = f"Connection failed"

    # Check InfluxDB connection
    try:
        influx_connector = InfluxDBConnector(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG, bucket=INFLUXDB_BUCKET)
        influx_connector.write_data(measurement="web_status_check", tags={"service": "web"}, fields={"status": 1})
        status_info['influxdb'] = "Connected"
        influx_connector.close()
    except Exception as e:
        status_info['influxdb'] = f"Connection failed"

    # Check PostgreSQL connection
    try:
        pg_connector = PostgreSQLConnector(
            dbname=PG_DBNAME,
            user=PG_USER,
            password=PG_PASSWORD,
            host=PG_HOST,
            port=PG_PORT
        )
        pg_connector.connect()
        if pg_connector.conn:
            status_info['postgresql'] = "Connected"
            pg_connector.close()
        else:
            status_info['postgresql'] = "Connection failed"
    except Exception as e:
        status_info['postgresql'] = f"Connection failed"

    return jsonify(status_info)

@app.route('/api/economic-events')
def api_economic_events():
    
    try:
        events_df = get_economic_events(days_ahead=7)
        if not events_df.empty:
            high_impact_df = events_df[events_df['importance'] == 'high'].copy()
            # Convert dataframe to a list of dicts for JSON serialization
            high_impact_df['time'] = high_impact_df['time'].astype(str)
            events_json = high_impact_df.to_dict(orient='records')
            return jsonify(events_json)
        else:
            return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/open-positions')
def api_open_positions():
    
    try:
        pg_connector = PostgreSQLConnector(
            dbname=PG_DBNAME,
            user=PG_USER,
            password=PG_PASSWORD,
            host=PG_HOST,
            port=PG_PORT
        )
        pg_connector.connect()
        # Assuming a 'trades' table with a 'status' column indicating 'open' or 'closed'
        # Adjust query based on your actual schema
        query = "SELECT * FROM trades WHERE status = 'open'"
        open_positions = pg_connector.fetch_all(query)
        pg_connector.close()
        
        # Convert list of tuples to list of dictionaries for better JSON representation
        # Assuming column names are known or can be fetched from cursor.description
        if open_positions:
            # This is a simplified way; a more robust solution would map columns dynamically
            # For now, let's assume a fixed structure or fetch column names
            # Example: (id, symbol, type, volume, entry_price, current_price, status, ...) 
            # For demonstration, let's just return the raw tuples for now, 
            # or we can define a simple mapping if the schema is fixed.
            # Let's assume a simple schema for now for demonstration purposes.
            # If the schema is dynamic, we'd need to fetch cursor.description
            columns = ["id", "symbol", "type", "volume", "entry_price", "current_price", "status", "take_profit", "stop_loss", "timestamp"]
            positions_dicts = []
            for pos in open_positions:
                positions_dicts.append(dict(zip(columns, pos)))
            return jsonify(positions_dicts)
        else:
            return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/send_message', methods=['GET', 'POST'])
def send_message():

    message_status = None
    if request.method == 'POST':
        message = request.form['message']
        try:
            publisher = Publisher(BROKER_HOST, BROKER_PORT, BROKER_USER, BROKER_PASS)
            publisher.connect()
            publisher.publish_message("web_queue", message)
            message_status = "Message sent successfully!"
            publisher.close()
        except Exception as e:
            message_status = f"Failed to send message: {e}"

    return render_template('send_message.html', message_status=message_status)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)