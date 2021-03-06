import json
import requests
import logging
import time
import os
from threading import Thread

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

if not os.path.isfile("config.json"):
    logging.error("'config.json' not found, refer to 'README.md'.")
    exit()

with open("config.json", "r") as cfg:
    config = json.load(cfg)

# check if everything is there
assert config["email"]
assert config["api_key"]
assert config["zones"]
assert config["query_every_seconds"]

headers = {"X-Auth-Email":config["email"], "X-Auth-Key":config["api_key"]}
base_url = "https://api.cloudflare.com/client/v4"


def update_records():
    records = []

    # first we get the records that we need to update

    json_response = []
    for zone in config["zones"]:
        response = requests.get(f"{base_url}/zones/{zone}/dns_records", headers=headers)
        if response.ok:
            for record in response.json()["result"]:
                json_response.append(record)
        else:
            raise Exception(f"Could not get dns records; response {response.status_code}")

    
    for record in json_response:
        if record["type"] == "A" or "CNAME":
            records.append(record)



    # we got the records we want to update, lets check if they are up to date, if not then update them
    patched_count = 0
    current_ip = get_ip()
    for record in records:
        if record["content"] != current_ip:

            data = json.dumps({"content":current_ip}) # content = ip
            resp = requests.patch(f"{base_url}/zones/{record['zone_id']}/dns_records/{record['id']}", headers=headers, data=data)
            patched_count+=1
            if not resp.ok:
                raise Exception(f"Could not patch record(s); code {resp.status_code}")
    
    if patched_count:
        logging.info(f"Sucessfully patched {patched_count} records")

def get_ip(): # beautiful
    while True:
        response = requests.get("https://api.ipify.org?format=json")
        if response.ok:
            #logging.info("Successfully grabbed ip") console spam, but i probably should fix the logic so it doesnt request spam... TOO BAD!
            return response.json()["ip"]
        else:
            logging.info(f"HTTP code {response.status_code} when trying to get ip, retrying in 5 seconds")
            time.sleep(5)
            continue

def auto_check_worker():
    logging.info(f"Worker started; checking for new IP every {config['query_every_seconds']} seconds")
    while True:
        try:
            update_records()
        except Exception as err:
            logging.error(f"Encountered an error - {err} - continuing")
            continue
        time.sleep(config["query_every_seconds"])

Thread(target=auto_check_worker).start()

