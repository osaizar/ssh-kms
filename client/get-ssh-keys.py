#!/usr/bin/python3

import sys
import os
import shutil
import requests

SSHD_CONF = "/etc/ssh/sshd_config"
URL = "{URL}"

CLIENT_PATH = "/usr/bin/get-ssh-keys"


def get_ssh_keys(user):
    hostname = os.uname()[1]

    print({"user" : user, "hostname" : hostname})

    resp = requests.post(URL, json={"user" : user, "hostname" : hostname})

    if not resp.status_code == 200:
        sys.exit(1)

    for r in resp.json()["ssh-keys"]:
        print(r)

    sys.exit(0)


def install():
    if os.getuid() != 0:
        print("[!] Run the installation client as root!")
        sys.exit(1)
    
    print(f"[+] Copying the client to {CLIENT_PATH}")
    client_path = os.path.abspath( __file__ )
    shutil.copy(client_path, CLIENT_PATH)

    print("[+] Setting the correct permissions")
    os.chmod(CLIENT_PATH, 0o755)
    os.chown(CLIENT_PATH, 0, 0)
    
    print("[+] Configuring AuthorizedKeysCommand in sshd_config")
    sshd_config = open(SSHD_CONF, "r").read()
    sshd_config = sshd_config.replace("#AuthorizedKeysCommand none", f"AuthorizedKeysCommand {CLIENT_PATH} --get-key %u")
    sshd_config = sshd_config.replace("#AuthorizedKeysCommandUser nobody", "AuthorizedKeysCommandUser nobody")

    with open(SSHD_CONF, "w") as s:
        s.write(sshd_config)
    
    print("[+] Done!")
    print("[+] Please restart the sshd service for the changes to take effect: `systemctl restart sshd`")
    sys.exit(0)


def uninstall():
    if os.getuid() != 0:
        print("[!] Run the uninstallation client as root!")
        sys.exit(1)
    
    print(f"[+] Delting {CLIENT_PATH}")
    client_path = os.path.abspath( __file__ )
    os.remove(CLIENT_PATH)
    
    print("[+] Commenting AuthorizedKeysCommand in sshd_config")
    sshd_config = open(SSHD_CONF, "r").read()
    sshd_config = sshd_config.replace(f"AuthorizedKeysCommand {CLIENT_PATH} --get-key %u", "#AuthorizedKeysCommand none")
    sshd_config = sshd_config.replace("AuthorizedKeysCommandUser nobody", "#AuthorizedKeysCommandUser nobody")

    with open(SSHD_CONF, "w") as s:
        s.write(sshd_config)
    
    print("[+] Done!")
    print("[+] Please restart the sshd service for the changes to take effect: `systemctl restart sshd`")
    sys.exit(0)


def print_help():
    print(f"[!] Usage: {__file__} --get-key <username> | --install | --uninstall")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
    else:
        print_help()
        sys.exit(1)

    if arg == "--install":
        install()
    elif arg == "--uninstall":
        uninstall()
    elif arg == "--get-key":
        if len(sys.argv) != 3:
            print_help()
            sys.exit(1)
        user = sys.argv[2]
        get_ssh_keys(user)
    else:
        print_help()