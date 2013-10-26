#!/usr/bin/env python

from imapclient import IMAPClient
from logging import basicConfig, getLogger, DEBUG
import argparse
import getpass
import os.path
from datetime import date, timedelta

logger = None

__cache__ = None
def ensure_folder_exists(server, folder_name):
    def regen_cache():
        global __cache__
        __cache__ = set()
        for (flags, delimiter, name) in server.list_folders():
            __cache__.add(name)
    if __cache__ is None:
        regen_cache()
    if folder_name not in __cache__:
        server.create_folder(folder_name)
        logger.info("Created folder '{folder_name}'".format(**locals()))
        regen_cache()

def messages_older_than_two_months(server):
    today = date.today()
    start_of_last_month = date(today.year, today.month, 1)
    logger.info("Getting messages from before {start_of_last_month}".format(
        start_of_last_month=start_of_last_month.isoformat()))
    for message_uid in server.search("BEFORE {date}".format(
            date=start_of_last_month.strftime("%d-%b-%Y"))):
        yield message_uid

def move_message_to_archives(server, message_uid):
    message_date = server.fetch([message_uid], ['INTERNALDATE'])[message_uid]['INTERNALDATE']
    archive_folder = "{subfolder}".format(subfolder=message_date.strftime("Archives.%Y-%m"))
    ensure_folder_exists(server, archive_folder)
    result = server._imap.uid("COPY", message_uid, archive_folder)
    if result[0] == "OK":
        result = server._imap.uid("STORE", message_uid, "+FLAGS", "(\Deleted)")
        result = server._imap.uid("EXPUNGE", message_uid)
    logger.info("Moved message {message_uid} to {archive_folder}".format(**locals()))

def organise(host, username, password, folder):
    server = IMAPClient(host, ssl=True)
    logger.info("Connected to server")
    server.login(username, password)
    logger.info("Logged in as {username}".format(**locals()))
    ensure_folder_exists(server, "Archives")
    server.select_folder(folder)
    for message_uid in messages_older_than_two_months(server):
        move_message_to_archives(server, message_uid)
    server.logout()
    logger.info("Logged out")

if __name__ == "__main__":
    basicConfig(level=DEBUG)
    logger = getLogger("mail_archiver")
    parser = argparse.ArgumentParser(
        description="Organise IMAP mail by month")
    parser.add_argument("host", type=str)
    parser.add_argument("username", type=str)
    parser.add_argument("folder", type=str, default="INBOX")
    args = parser.parse_args()
    if os.path.exists(os.path.expanduser("~/.mail_sorter_password")):
        logger.info("~/.mail_sorter_password exists")
        with open(os.path.expanduser("~/.mail_sorter_password")) as password_file:
            password = password_file.read().strip()
    else:
        logger.info("~/.mail_sorter_password does not exist")
        password = getpass.getpass()
    organise(args.host, args.username, password, args.folder)
