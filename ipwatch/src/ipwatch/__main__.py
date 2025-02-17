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
from collections import namedtuple

from . import ipgetter

################
### CLASSES ####
################

SCRIPTDIR = Path(__file__).parent


def readconfig(fname):
    config = ConfigParser()
    config.read(fname)
    config = config["DEFAULT"]
    Config = namedtuple("Config", config)
    return Config(**config)


def isipaddr(ipstr):
    """True is ipstr matches x.x.x.x"""
    pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    return pattern.match(ipstr)


def isinblacklist(ip, blacklist):
    blacklist = blacklist.split(",")
    for black_ip in blacklist:
        if fnmatch(ip, black_ip):
            logging.warning( "GetIP: Bad IP (in Blacklist): %s in %s", ip, black_ip,)
            return True

    return False

# return the current external IP address
def getips(try_count, blacklist):
    "Function to return the current, external, IP address"


    # try up to config.try_count servers for an IP
    for counter in range(int(try_count)):

        # get an IP
        external_ip, local_ip, server = ipgetter.myip()

        # check to see that it has a ###.###.###.### format
        if not isipaddr(external_ip):
            logging.warning( "GetIP: Try %d:  Bad IP    (malformed): %s", counter + 1, external_ip)
            continue

        if isinblacklist(external_ip, blacklist):
            continue

        logging.warning("GetIP: Try %d: Good IP: %s", counter + 1, external_ip)
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
    receiver_emails,
    machine,
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

    for email in receiver_emails.split(","):
        subprocess.check_output(
            ["/usr/bin/mail", "-s", f"new ip: {new_external_ip}", f"{email}"],
            input=mailbody,
            text=True,
        )


################
##### MAIN #####
################


def main():
    # parse arguments
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", dest="config_file", default=SCRIPTDIR / "config.txt"
    )
    args = parser.parse_args()

    # read config file
    print("Reading ", args.config_file)
    config = readconfig(args.config_file)

    save_ip_path = Path(config.save_ip_path)
    if not save_ip_path.is_absolute():
        save_ip_path = SCRIPTDIR / save_ip_path

    old_external_ip, old_local_ip = getoldips(save_ip_path)
    curr_external_ip, curr_local_ip, server = getips(
        int(config.try_count), config.ip_blacklist
    )

    # check to see if the IP address has changed
    if (curr_external_ip != old_external_ip) or (curr_local_ip != old_local_ip):
        # send email
        print("Current IP differs from old IP.")
        sendmail(
            old_external_ip,
            old_local_ip,
            curr_external_ip,
            curr_local_ip,
            server,
            config.receiver_email,
            config.machine,
        )

        # updatefile
        updateoldips(save_ip_path, curr_external_ip, curr_local_ip)

    else:
        print("Current IP = Old IP.  No need to send email.")


if __name__ == "__main__":
    main()
