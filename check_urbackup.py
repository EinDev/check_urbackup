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
from datetime import datetime
import argparse
from enum import Enum
import re


class BackupStatus(Enum):
    OK = 0
    WARNING = 1
    CRITICAL = 2


# Parses a backup client's status using the data provided by the UrBackup server
# Returns: The BackupStatus of the client and a description if not OK
# max_fage and max_iage are the maximum image and file backup age (in days)
def get_status(client_data, maxfiledays, maximagedays) -> (BackupStatus, str):
    # If a backup is disabled, "*_disabled" is not set - we don't want a KeyError
    if "file_disabled" not in client_data:
        client_data["file_disabled"] = False
    if "image_disabled" not in client_data:
        client_data["image_disabled"] = False

    # Don't set file_ok to False if file_disabled is True
    if not client_data["file_ok"] and not client_data["file_disabled"]:
        file_failed = True
        file_str = "No recent backup"
    elif client_data["file_ok"]:
        file_failed = False
        file_str = "OK"
    else:
        file_failed = False
        file_str = "Disabled"

    # Don't set image_ok to False if image_disabled is True
    if not client_data["image_ok"] and not client_data["image_disabled"]:
        image_failed = True
        image_str = "No recent backup"
    elif client_data["image_ok"]:
        image_failed = False
        image_str = "OK"
    else:
        image_failed = False
        image_str = "Disabled"

    client_online = client_data["online"]
    client_name = client_data["name"]
    last_file_backup = datetime.fromtimestamp(client_data["lastbackup"])
    last_image_backup = datetime.fromtimestamp(client_data["lastbackup_image"])
    file_old = is_file_old(client_data, maxfiledays) if maxfiledays else False
    image_old = is_image_old(client_data, maximagedays) if maximagedays else False

    # Evaluate the backup status
    # client offline:
    #   backups OK? WARNING
    #   backups old or failed? CRITICAL
    # client online:
    #   backups OK? OK
    #   backups old or failed? CRITICAL
    any_backup_failed = file_failed or image_failed
    any_backup_old = file_old or image_old
    if not client_online:
        if any_backup_failed or any_backup_old:
            client_status = BackupStatus.CRITICAL
        else:
            client_status = BackupStatus.WARNING
    else:
        if not any_backup_failed and not any_backup_old:
            client_status = BackupStatus.OK
        else:
            client_status = BackupStatus.CRITICAL

    # Get a short description of the failed backup type if failed
    client_details = []
    if client_status != BackupStatus.OK:
        # Short description of the client
        client_details.append(f"<b>HostName: {client_name}</b>, Online: {client_online}")

        # File backup information, if failed or old
        if file_old:
            client_details.append(f"<b>Last Filebackup: {last_file_backup.strftime('%x %X')}</b>")
        if file_failed:
            client_details.append(f"<b>Status Filebackup: {file_str}</b>")

        # Image backup information, if failed or old
        if image_old:
            client_details.append(f"<b>Last Imagebackup: {last_image_backup.strftime('%x %X')}</b>")
        if image_failed:
            client_details.append(f"<b>Status Imagebackup: {image_str}</b>")

    return client_status, ", ".join(client_details)


def is_file_old(client_data, max_days):
    disabled = client_data["file_disabled"]
    last_backup = datetime.fromtimestamp(client_data["lastbackup"])
    diff = datetime.now() - last_backup
    diff_hours = int(diff.seconds / 60 / 60)
    return diff_hours / 24 > max_days and not disabled


def is_image_old(client_data, max_days):
    disabled = client_data["image_disabled"]
    last_backup = datetime.fromtimestamp(client_data["lastbackup_image"])
    diff = datetime.now() - last_backup
    diff_hours = int(diff.seconds / 60 / 60)
    return diff_hours / 24 > max_days and not disabled


# Gets the global status and details from get_status()
# client_pattern is a regex-pattern for client name(s)
def get_global_status(client_array, client_pattern: str = ".*"):
    global_details = ""
    regex = re.compile(client_pattern)
    global_status = BackupStatus.OK
    for client in client_array:
        if regex.fullmatch(client["name"]):
            client_status, client_details = get_status(client, args.maxfiledays, args.maximagedays)
            if client_status == BackupStatus.OK:
                continue
            # If the global_status is CRITICAL, we don't want to change it back to WARNING
            elif client_status == BackupStatus.WARNING and global_status != BackupStatus.CRITICAL:
                global_status = BackupStatus.WARNING
                global_details += client_details + "\n"
            else:
                global_status = BackupStatus.CRITICAL
                global_details += client_details + "\n"
    return global_status, global_details



parser = argparse.ArgumentParser()
parser.add_argument('--version', '-v', action="store_true", help='show agent version')
parser.add_argument('--host', '-ho', action="append", help='host name or IP')
parser.add_argument('--user', '-u', action="append", help='User name for Urbackup server')
parser.add_argument('--password', '-p', action="append", help='user password for Urbackup server')
parser.add_argument('--client', '-c', action="append", help='backup client name (Regular Expression)')
parser.add_argument('--maxfiledays', '-f', action="append", help='maximum age of file backup')
parser.add_argument('--maximagedays', '-i', action="append", help='maximum age of image backup')
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
