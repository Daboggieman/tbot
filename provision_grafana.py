
import requests
import json
import getpass

GRAFANA_URL = "http://localhost:3000"
ADMIN_USER = "admin"

ADMIN_PASSWORD = getpass.getpass("Enter Grafana admin password: ")

HEADERS = {
    "Content-Type": "application/json"
}

# Create Bot Monitoring Dashboard
def create_bot_monitoring_dashboard():
    url = f"{GRAFANA_URL}/api/dashboards/db"
    with open("grafana_provisioning/dashboards/grafana_dashboard.json", "r") as f:
        dashboard_json = json.load(f)

    payload = {
        "dashboard": dashboard_json,
        "folderId": 0, # General folder
        "overwrite": True
    }
    response = requests.post(url, auth=(ADMIN_USER, ADMIN_PASSWORD), headers=HEADERS, data=json.dumps(payload))
    if response.status_code == 200:
        print("Bot Monitoring dashboard created successfully.")
    else:
        print(f"Failed to create Bot Monitoring dashboard. Status code: {response.status_code}, Response: {response.text}")

if __name__ == "__main__":
    create_bot_monitoring_dashboard()
