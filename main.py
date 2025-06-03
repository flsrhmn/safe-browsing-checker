import os
import requests
import json
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.cloud import secretmanager

# Initialize Secret Manager client
client = secretmanager.SecretManagerServiceClient()

def access_secret(secret_name):
    """Access secret version"""
    name = f"projects/safe-browsing-check-461816/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def check_url(api_key, url):
    """Check URL safety"""
    endpoint = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
    payload = {
        "client": {"clientId": "torazzo", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}]
        }
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(
        f"{endpoint}?key={api_key}",
        data=json.dumps(payload),
        headers=headers
    )
    return "matches" not in response.json()

def send_alert(url, platform, secrets):
    """Send alerts"""
    message = f"🚨 SAFE BROWSING ALERT!\nSite changed to UNSAFE: {url}"
    
    if platform == "telegram":
        token = secrets["TELEGRAM_TOKEN"]
        chat_id = secrets["TELEGRAM_CHAT_ID"]
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": message}
        )
    
    elif platform == "discord":
        webhook = secrets["DISCORD_WEBHOOK"]
        requests.post(webhook, json={"content": message})
    
    elif platform == "email":
        msg = MIMEMultipart()
        msg['From'] = secrets["EMAIL_SENDER"]
        msg['To'] = secrets["ALERT_EMAILS"]
        msg['Subject'] = "URGENT: Site Safety Alert"
        msg.attach(MIMEText(message, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(secrets["EMAIL_SENDER"], secrets["EMAIL_PASSWORD"])
        server.sendmail(secrets["EMAIL_SENDER"], secrets["ALERT_EMAILS"].split(','), msg.as_string())
        server.quit()

def main():
    # Load secrets
    secrets = {
        "SAFE_BROWSING_API_KEY": access_secret("SAFE_BROWSING_API_KEY"),
        "TELEGRAM_TOKEN": access_secret("TELEGRAM_TOKEN"),
        "TELEGRAM_CHAT_ID": access_secret("TELEGRAM_CHAT_ID"),
        "DISCORD_WEBHOOK": access_secret("DISCORD_WEBHOOK"),
        "ALERT_EMAILS": access_secret("ALERT_EMAILS"),
        "EMAIL_SENDER": access_secret("EMAIL_SENDER"),
        "EMAIL_PASSWORD": access_secret("EMAIL_PASSWORD"),
        "URLS": access_secret("URLS")
    }
    
    # Load previous statuses from Cloud Storage
    status_file = "site_status.json"
    try:
        # In Cloud Run, use /tmp for ephemeral storage
        with open(f"/tmp/{status_file}", "r") as f:
            site_status = json.load(f)
    except:
        site_status = {}

    # Check URLs
    for url in secrets["URLS"].split(','):
        url = url.strip()
        is_safe = check_url(secrets["SAFE_BROWSING_API_KEY"], url)
        current_status = "safe" if is_safe else "unsafe"
        
        if url in site_status:
            if site_status[url] == "safe" and current_status == "unsafe":
                print(f"ALERT: {url} became unsafe!")
                send_alert(url, "telegram", secrets)
                send_alert(url, "discord", secrets)
                send_alert(url, "email", secrets)
        
        site_status[url] = current_status
        time.sleep(1)  # Avoid API limits

    # Save statuses
    with open(f"/tmp/{status_file}", "w") as f:
        json.dump(site_status, f)

if __name__ == "__main__":
    main()
