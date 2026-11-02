#!/usr/bin/env python3
"""Read-only Microsoft Graph access to an Outlook mailbox.

Usage:
  graph_mail.py login                 # device-code sign-in (one time)
  graph_mail.py folders               # list mail folders
  graph_mail.py newsletters [days]    # dump messages of "AI & Business Newsletter" (default 7 days) as JSON
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import msal
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(HERE, "token_cache.json")
# Public client ID of Microsoft Graph Command Line Tools (supports personal accounts + device code).
CLIENT_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"
AUTHORITY = "https://login.microsoftonline.com/consumers"
SCOPES = ["Mail.Read"]
FOLDER_NAME = os.environ.get("NEWSLETTER_FOLDER", "AI & Business Newsletter")
GRAPH = "https://graph.microsoft.com/v1.0"


def load_cache():
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            cache.deserialize(f.read())
    return cache


def save_cache(cache):
    if cache.has_state_changed:
        fd = os.open(CACHE_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(cache.serialize())


def app_and_cache():
    cache = load_cache()
    return msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache), cache


def login():
    app, cache = app_and_cache()
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        sys.exit("Device flow failed: " + json.dumps(flow))
    print(f"CODE={flow['user_code']} URL={flow['verification_uri']}", flush=True)
    result = app.acquire_token_by_device_flow(flow)
    save_cache(cache)
    if "access_token" not in result:
        sys.exit("Login failed: " + result.get("error_description", str(result)))
    print("LOGIN_OK", result.get("id_token_claims", {}).get("preferred_username", ""), flush=True)


def token():
    app, cache = app_and_cache()
    accounts = app.get_accounts()
    result = app.acquire_token_silent(SCOPES, account=accounts[0]) if accounts else None
    save_cache(cache)
    if not result or "access_token" not in result:
        sys.exit("AUTH_EXPIRED: run `graph_mail.py login` again")
    return result["access_token"]


def get(url, params=None):
    r = requests.get(url, headers={"Authorization": "Bearer " + token(), "Prefer": 'outlook.body-content-type="text"'},
                     params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def clean(text):
    # Drop tracking links and invisible padding, collapse blank lines to keep the payload small.
    text = re.sub(r"<?https?://\S+>?", "", text)
    text = re.sub(r"[͏­​-‏⁠﻿]+", "", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def all_folders():
    out, url = [], f"{GRAPH}/me/mailFolders"
    params = {"$top": 100, "includeHiddenFolders": "false"}
    while url:
        data = get(url, params)
        out += data.get("value", [])
        url, params = data.get("@odata.nextLink"), None
    return out


def newsletters(days):
    folder = next((f for f in all_folders() if f["displayName"] == FOLDER_NAME), None)
    if not folder:
        sys.exit(f"Folder not found: {FOLDER_NAME}")
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"{GRAPH}/me/mailFolders/{folder['id']}/messages"
    params = {"$filter": f"receivedDateTime ge {since}", "$orderby": "receivedDateTime desc", "$top": 50,
              "$select": "subject,from,receivedDateTime,body"}
    msgs = []
    while url:
        data = get(url, params)
        for m in data.get("value", []):
            msgs.append({
                "from": m.get("from", {}).get("emailAddress", {}).get("name"),
                "received": m.get("receivedDateTime"),
                "subject": m.get("subject"),
                "body": clean(m.get("body", {}).get("content") or "")[:8000],
            })
        url, params = data.get("@odata.nextLink"), None
    print(json.dumps(msgs, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "login":
        login()
    elif cmd == "folders":
        print("\n".join(f"{f['displayName']} ({f.get('totalItemCount')})" for f in all_folders()))
    elif cmd == "newsletters":
        newsletters(int(sys.argv[2]) if len(sys.argv) > 2 else 7)
    else:
        sys.exit(__doc__)
