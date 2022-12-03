#!/usr/bin/python3

import sys
import requests

URL = "http://localhost:5000"

user = sys.argv[1]
hostname = sys.argv[2]

resp = requests.post(URL, json={"user" : user, "hostname" : hostname})

if not resp.status_code == 200:
    sys.exit(1)

for r in resp.json()["ssh-keys"]:
    print(r)

sys.exit(0)