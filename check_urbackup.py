#!/usr/bin/env python3.8
# Written By: Timon Michel (Xtek)
# Based on: tbaror/check_urbackup by Tal Bar-Or
# Last Modified - 15/10/2020
# check_urbackup for backup status
# Ver 0.11 import urbackup_api
# simple script to check Urbackup backup status used by https://github.com/uroni/urbackup-server-python-web-api-wrapper

import sys

# Python 3.8 is necessary for this check, so we are including it to the path

sys.path.insert(0, '/usr/lib/python3.8')

import urbackup_api
import datetime
import argparse
from enum import Enum
import re


class BackupStatus(Enum):
    OK = 0
    WARNING = 1
    CRITICAL = 2


# Parses a backup client's status using the data provided by the UrBackup server
# Returns: The BackupStatus of the client and a description if not OK
def get_status(client_data) -> (BackupStatus, str):
    # If a backup is disabled, "*_disabled" is not set - we don't want a KeyError
    if "file_disabled" not in client_data:
        client_data["file_disabled"] = False
    if "image_disabled" not in client_data:
        client_data["image_disabled"] = False

    # Don't set file_ok to False if file_disabled is True
    if not client_data["file_ok"] and not client_data["file_disabled"]:
        file_ok = False
        file_str = "No recent backup"
    elif client_data["file_ok"]:
        file_ok = True
        file_str = "OK"
    else:
        file_ok = True
        file_str = "Disabled"

    # Don't set image_ok to False if image_disabled is True
    if not client_data["image_ok"] and not client_data["image_disabled"]:
        image_ok = False
        image_str = "No recent backup"
    elif client_data["image_ok"]:
        image_ok = True
        image_str = "OK"
    else:
        image_ok = True
        image_str = "Disabled"

    client_online = client_data["online"]
    client_name = client_data["name"]
    last_file_backup = datetime.datetime.fromtimestamp(client_data["lastbackup"])
    last_file_backup_str = last_file_backup.strftime("%x %X")
    last_image_backup = datetime.datetime.fromtimestamp(client_data["lastbackup_image"])
    last_image_backup_str = last_image_backup.strftime("%x %X")

    # Evaluate the backup status
    if not client_online:
        if file_ok and image_ok:
            client_status = BackupStatus.WARNING
        else:
            client_status = BackupStatus.CRITICAL
    else:
        if file_ok and image_ok:
            client_status = BackupStatus.OK
        else:
            client_status = BackupStatus.CRITICAL

    # Get a short description of the failed backup type if failed
    client_details = ""
    if client_status != BackupStatus.OK:
        client_details += f"<b>HostName: {client_name}</b>, Online: {client_online}"
        if not file_ok or not image_ok:
            client_details += ", "
        if not file_ok:
            client_details += f"Last Filebackup: {last_file_backup_str}, <b>Status Filebackup: {file_str}</b>"
            if not image_ok:
                client_details += ", "
        if not image_ok:
            client_details += f"Last Imagebackup: {last_image_backup_str}, <b>Status Imagebackup: {image_str}</b>"
    return client_status, client_details


# Gets the global status and details from get_status()
# client_pattern is a regex-pattern for client name(s)
def get_global_status(client_array, client_pattern: str = ".*"):
    global_details = ""
    regex = re.compile(client_pattern)
    global_status = BackupStatus.OK
    for client in client_array:
        if regex.fullmatch(client["name"]):
            client_status, client_details = get_status(client)
            if client_status == BackupStatus.OK:
                continue
            # If the global_status is CRITICAL, we don't want to change it back to WARNING
            elif client_status == BackupStatus.WARNING and global_status != BackupStatus.CRITICAL:
                global_status = BackupStatus.WARNING
                global_details += client_details + "\n"
            else:
                global_status = BackupStatus.CRITICAL
                global_details += client_details + "\n"
    return global_status


parser = argparse.ArgumentParser()
parser.add_argument('--version', '-v', action="store_true", help='show agent version')
parser.add_argument('--host', '-ho', action="append", help='host name or IP')
parser.add_argument('--user', '-u', action="append", help='User name for Urbackup server')
parser.add_argument('--password', '-p', action="append", help='user password for Urbackup server')
parser.add_argument('--client', '-c', action="append", help='backup client name (Regular Expression)')
args = parser.parse_args()

if args.host:
    try:
        server = urbackup_api.urbackup_server("http://" + args.host[0] + ":55414/x", args.user[0], args.password[0])
        clients = server.get_status()
        client_regex = args.client or ".*"
        status, details = get_global_status(clients, client_regex)
        if status == BackupStatus.CRITICAL:
            print("CRITICAL: " + details)
            sys.exit(2)
        elif status == BackupStatus.WARNING:
            print("WARNING: " + details)
            sys.exit(1)
        elif status == BackupStatus.OK:
            print("OK")
            sys.exit(0)
    except Exception as e:
        print("Error Occured: ", e)
    print("UNKOWN")
    sys.exit(3)


elif args.version:
    print('1.1 Urback Check, Written By: Timon Michel (Xtek), Based on: tbaror/check_urbackup by Tal Bar-Or')
    sys.exit()
else:
    print("please run check --host <IP OR HOSTNAME> [--user <username>] [--password <password>] [--client <client_regex>]"
          "\nor use --help")
    sys.exit()
