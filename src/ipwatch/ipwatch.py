# USAGE: python3 ipwatch.py [config]
# USAGE: ./ipwatch.py [config]
#
# [config] = path to an IPWatch configuration file
#
# Sean Begley
# 2021-07-19
# v0.9
#
# This program gets for your external IP address
# checks it against your "saved" IP address and,
# if a difference is found, emails you the new IP.
# This is useful for servers at residential locations
# whose IP address may change periodically due to actions
# by the ISP.

# REFERENCES
# https://github.com/phoemur/ipgetter

import logging
import re
import subprocess
from configparser import ConfigParser
from fnmatch import fnmatch
from pathlib import Path
from textwrap import dedent
import platform
import time

from . import ipgetter

def make_parser():
    import argparse

    parser = argparse.ArgumentParser(description=f"""
This program gets for your external IP address
checks it against your "saved" IP address and,
if a difference is found, emails you the new IP.
This is useful for servers at residential locations
whose IP address may change periodically due to actions
by the ISP.
""",
)

    parser.add_argument(
        "--config-file",
        help="read email-adresses, machine name, blacklist and try count from this file",
    )

    parser.add_argument("--receiver-email", default="root", help="receiver email-address")
    parser.add_argument("--machine", default=platform.node(), help="machine name (e.g. 'Home NAS')")
    parser.add_argument("--try-count", type=int, default=10, help="try count")
    parser.add_argument("--ip-blacklist", default="192.168.*.*,10.*.*.*", help="ip blacklist")
    parser.add_argument("--repeat", type=int, default=0, help="when >0, repeat every N seconds")
    parser.add_argument("--dry-run", action="store_true", help="do not send email")
    parser.add_argument("--verbose", help="increase logging verbosity", action="store_const", const=logging.INFO)
    parser.add_argument("--force", help="always report external ip, even if unchanged", action="store_true")

    return parser

def read_config(fname, parser):
    logging.info("Reading %s", fname)
    config = ConfigParser()
    config.read_string("[DEFAULT]\n" + open(fname, "r").read())
    config = config["DEFAULT"]

    def getentry(config, action):
        value = config.get(action.dest, action.default)
        return action.type(value) if action.type else value

    return {
        c.dest : getentry(config, c)
        for c in parser._actions
    }

def isipaddr(ipstr):
    """True if ipstr matches x.x.x.x"""
    pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    return pattern.match(ipstr)


def isinblacklist(ip, blacklist, server = '?'):
    blacklist = blacklist.split(",")
    for black_ip in blacklist:
        if fnmatch(ip, black_ip):
            logging.warning( "GetIP from %s: Bad IP (in Blacklist): %s in %s", server, ip, black_ip,)
            return True

    return False

# return the current external IP address
def getips(try_count, blacklist):
    "Function to return the current, external, IP address"

    # try up to try_count servers for an IP
    for counter in range(try_count):

        # get an IP
        external_ip, local_ip, server = ipgetter.myip()

        # check to see that it has a ###.###.###.### format
        if not isipaddr(external_ip):
            logging.warning( "GetIP: Try %d:  Bad IP    (malformed): %s", counter + 1, external_ip)
            continue

        if isinblacklist(external_ip, blacklist, server=server):
            continue

        logging.info("GetIP: Try %d: Good IP: %s", counter + 1, external_ip)
        return external_ip, local_ip, server

    raise ValueError("Could not get IPs")


# get old IP address
def getoldips(filepath):
    "Function to get the old ip address from savefile"

    # check if the savefile exists
    if not Path(filepath).is_file():
        return None, None

    with open(filepath) as infile:
        old_external_ip, old_local_ip = (line.strip() for line in infile)
        assert isipaddr(old_external_ip) and isipaddr(old_local_ip)

    return old_external_ip, old_local_ip


# write the new IP address to file
def updateoldips(filepath, new_external_ip, new_local_ip):
    "Function to update the old ip address from savefile"

    filepath.parent.mkdir(exist_ok=True, parents=True)
    with open(filepath, "w") as savefile:
        savefile.write(new_external_ip)
        savefile.write("\n")
        savefile.write(new_local_ip)


# send mail with new IP address
def sendmail(
    old_external_ip,
    old_local_ip,
    new_external_ip,
    new_local_ip,
    server,
    email,
    machine,
    dry_run = False,
):
    "Function to send an email with the new IP address"

    mailbody = dedent(
        f"""
     The IP address of {machine} has changed:
       Old external IP = {old_external_ip}
       Old local IP = {old_local_ip}
       New external IP: {new_external_ip}
       New local IP = {new_local_ip}
       The Server queried was {server}"""
    )

    emails = email.split(",")
    subject = f"new ip: {new_external_ip}"
    dryrun_notice = "[DRYRUN] " if dry_run else ""
    logging.info("%sSending mail to %s with subject %s:\n%s",dryrun_notice, email, subject, mailbody)

    if not dry_run:
        subprocess.check_output(
            ["/usr/bin/mail", "-s", subject, ] + emails,
            input=mailbody,
            text=True,
        )


################
##### MAIN #####
################


def main():
    # parse arguments
    import platformdirs

    default_config_file = platformdirs.user_config_path("ipwatch") / "config.txt"

    parser = make_parser()

    args = parser.parse_args()
    if args.config_file is not None:
        parser.set_defaults(**read_config(args.config_file, parser))
    elif default_config_file.exists():
        parser.set_defaults(**read_config(default_config_file, parser))
    args = parser.parse_args()

    logging.basicConfig(level=args.verbose)

    save_ip_path = platformdirs.user_cache_path("ipwatch") / "saved_ip.txt"

    while True:
        old_external_ip, old_local_ip = getoldips(save_ip_path)
        curr_external_ip, curr_local_ip, server = getips(
           args.try_count, args.ip_blacklist
        )

        # check to see if the IP address has changed
        if (curr_external_ip != old_external_ip) or \
        (curr_local_ip != old_local_ip) or \
            args.force:
            # send email
            logging.info("Current IP differs from old IP.")
            sendmail(
                old_external_ip,
                old_local_ip,
                curr_external_ip,
                curr_local_ip,
                server,
                args.receiver_email,
                args.machine,
                dry_run = args.dry_run,
            )

            # updatefile
            updateoldips(save_ip_path, curr_external_ip, curr_local_ip)

        else:
            logging.info("Current IP = Old IP.  No need to send email.")

        if args.repeat <= 0:
            break
        else:
            time.sleep(args.repeat)


if __name__ == "__main__":
    main()
