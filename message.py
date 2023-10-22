import requests
import json
import datetime
from pytz import timezone
import pytz
import time

# Replace with your .ROBLOSECURITY cookie
roblox_cookie = ""

# Discord webhook URL
discord_webhook_url = ""


def get_csrf_token(cookie):
    response = requests.post('https://accountsettings.roblox.com/v1/email', cookies={".ROBLOSECURITY": cookie})
    csrf = response.headers.get('x-csrf-token')
    return csrf


def get_logged_in_username(cookie):
    headers = {
        'x-csrf-token': get_csrf_token(cookie),
        'accept': 'application/json'
    }
    response = requests.get('https://users.roblox.com/v1/users/authenticated', headers=headers, cookies={".ROBLOSECURITY": roblox_cookie})
    user_data = response.json()
    if "displayName" in user_data:
        return user_data["displayName"]
    return "Unknown"

def get_id(cookie):
    headers = {
        'x-csrf-token': get_csrf_token(cookie),
        'accept': 'application/json'
    }
    response = requests.get('https://users.roblox.com/v1/users/authenticated', headers=headers, cookies={".ROBLOSECURITY": roblox_cookie})
    user_data = response.json()
    if "displayName" in user_data:
        return user_data["id"]
    return None


def check_for_new_transactions(roblox_cookie, last_check_time, user_id):
    url = f"https://economy.roblox.com/v2/users/{user_id}/transactions?limit=10&transactionType=Purchase"
    headers = {
        'x-csrf-token': get_csrf_token(roblox_cookie),
        'accept': 'application/json'
    }
    response = requests.get(url, cookies={".ROBLOSECURITY": roblox_cookie})
    transactions = response.json()
    new_transactions = []
    if 'data' in transactions:
        for transaction in transactions['data']:
            created = transaction["created"]
            time_utc = datetime.datetime.fromisoformat(created)
            if time_utc > last_check_time:
                new_transactions.append(transaction)
    return new_transactions


def get_thumbnail_url(asset_id, is_bundle):
    if is_bundle:
        url = f"https://thumbnails.roblox.com/v1/bundles/thumbnails?bundleIds={asset_id}&size=150x150&format=Png&isCircular=false"
    else:
        url = f"https://thumbnails.roblox.com/v1/assets?assetIds={asset_id}&returnPolicy=PlaceHolder&size=30x30&format=Png&isCircular=false"
    response = requests.get(url)
    return response.json()["data"][0]["imageUrl"]


sent_transactions = set()

def send_to_discord(data):
    if data['seller_name'] not in sent_transactions:
        embed = {
            "title": f" New Roblox Purchase",
            "color": 10181046,  # Purple color
            "author": {
                "name": data['asset_name'],
                "icon_url": data['thumbnail_url']
            },
            "description": f" Seller: **{data['seller_name']}**",
            "fields": [
                {"name": "Robux Cost", "value": f"<:robuxnew:982469827342000148> {data['robux_cost']}", "inline": True},
                {"name": "Time (EST)", "value": data['time_est'], "inline": True},
            ],
            "footer": {"text": "Moon's Transaction Tracker ✨"}
        }
        payload = {
            "embeds": [embed]
        }
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(discord_webhook_url, data=json.dumps(payload), headers=headers)
        if response.status_code == 204:
            print("Data sent to Discord successfully.")
            sent_transactions.add(data['seller_name'])
        else:
            print("Failed to send data to Discord.")


def convert_to_est(time_str):
    time2 = datetime.datetime.fromisoformat(time_str)
    est = timezone('US/Eastern')
    time_est = time2.astimezone(est)
    return time_est.strftime('%Y-%m-%d %H:%M:%S')


print("Roblox Transaction Tracker Bot is starting...")
logged_in_username = get_logged_in_username(roblox_cookie)
print(f"Logged in as {logged_in_username}")
user_id = get_id(roblox_cookie)

# Record the time the script is started
script_start_time = datetime.datetime.now(pytz.utc)

while True:
   
    new_transactions = check_for_new_transactions(roblox_cookie, script_start_time, user_id)

    if new_transactions:
        for transaction in new_transactions:
            print("Found new transaction. Sending to webhook...")
            asset_id = transaction["details"]["id"]
            is_bundle = transaction["details"]["type"] == "Bundle"
            seller_id = transaction["agent"]["id"]
            seller_name = transaction["agent"]["name"]
            seller_thumbnail_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={seller_id}&size=48x48&format=Png&isCircular=true"
            robux_cost = transaction["currency"]["amount"]
            created = transaction["created"]

            thumbnail_url = get_thumbnail_url(asset_id, is_bundle)
            time_est = convert_to_est(created)

            data = {
                "seller_name": seller_name,
                "seller_thumbnail_url": seller_thumbnail_url,
                "asset_name": transaction["details"]["name"],
                "robux_cost": robux_cost,
                "time_est": time_est,
                "thumbnail_url": thumbnail_url
            }

            send_to_discord(data)

    else:
        print("Waiting for transactions...")


    time.sleep(20) 
