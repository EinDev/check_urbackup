# !/usr/bin/env python3.8
# Written By: Timon Michel (Xtek)
# Based on: tbaror/check_urbackup by Tal Bar-Or
# Created - 21/12/2016
# check_urbackup for backup status
# Ver 0.3 import urbackup_api
# simple script to check Urbackup backup status used by https://github.com/uroni/urbackup-server-python-web-api-wrapper
# source code found at https://bitbucket.org/tal_bar_or/check_urbackup
import sys
sys.path.insert(0, '/usr/lib/python3.8')
import urbackup_api
import datetime
import argparse

ClientPrint = ""
GlobalStatus = []
Globelstat = ""


def Statuscheck(client):
    global ClientPrint
    if "file_disabled" not in client:
        client["file_disabled"] = False
    if "image_disabled" not in client:
        client["image_disabled"] = False

    if not client["file_ok"] and not client["file_disabled"]:
        file_ok = False
        file_str = "<b>No recent backup</b>"
    elif client["file_ok"]:
        file_ok = True
        file_str = "OK"
    else:
        file_ok = True
        file_str = "Disabled"

    if not client["image_ok"] and not client["image_disabled"]:
        image_ok = False
        image_str = "<b>No recent backup</b>"
    elif client["image_ok"]:
        image_ok = True
        image_str = "OK"
    else:
        image_ok = True
        image_str = "Disabled"

    client_online = client["online"]
    client_name = client["name"]
    last_file_backup = datetime.datetime.fromtimestamp(client["lastbackup"])
    last_file_backup_str = last_file_backup.strftime("%x %X")
    last_image_backup = datetime.datetime.fromtimestamp(client["lastbackup_image"])
    last_image_backup_str = last_image_backup.strftime("%x %X")

    if not client_online:
        if file_ok and image_ok:
            client_status = "Warning"
        else:
            client_status = "Critical"
    else:
        if file_ok and image_ok:
            client_status = "OK"
        else:
            client_status = "Critical"
    if client_status != "OK":
        ClientPrint += f"HostName: {client_name}, Online: {client_online}, Status: {client_status}, " \
                       f"LastFileBackup: {last_file_backup_str}, FileStatus: {file_str}, " \
                       f"LastImageBackup: {last_image_backup_str}, ImageStatus: {image_str}\n"
    return client_status


parser = argparse.ArgumentParser()
parser.add_argument('--version', '-v', action="store_true", help='show agent version')
parser.add_argument('--host', '-ho', action="append", help='host name or IP')
parser.add_argument('--user', '-u', action="append", help='User name for Urbackup server')
parser.add_argument('--password', '-p', action="append", help='user password for Urbackup server')
args = parser.parse_args()

if args.host or args.user or args.password:
    try:
        server = urbackup_api.urbackup_server("http://" + args.host[0] + ":55414/x", args.user[0], args.password[0])
        clients = server.get_status()
        for client in clients:
            GlobalStatus.append(Statuscheck(client))
            Globelstat = set(GlobalStatus)
        while True:
            if "Critical" in Globelstat:
                # print(Globelstat)
                print("CRITICAL")
                print(ClientPrint)
                sys.exit(2)
            elif "Warning" in Globelstat:
                # print(Globelstat)
                print("WARNING")
                print(ClientPrint)
                sys.exit(1)
            elif "OK" in Globelstat:
                # print(Globelstat)
                print("OK")
                print(ClientPrint)
                sys.exit(0)
            else:
                print("UNKOWN")
                print(ClientPrint)
                sys.exit(3)
    except Exception as e:
        print("Error Occured: ", e)


elif args.version:
    print('1.1 Urback Check, Written By: Timon Michel (Xtek), Based on: tbaror/check_urbackup by Tal Bar-Or')
    sys.exit()
else:
    print("please run check --host <IP OR HOSTNAME> --user <username> --password <password>" + '\n or use --help')
    sys.exit()
