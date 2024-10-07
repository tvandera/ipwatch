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
import dataclasses

from . import ipgetter

################
### CLASSES ####
################

DEFAULT_TRY = "10"
DEFAULT_BLACKLIST = "192.168.*.*,10.*.*.*"

EXAMPLE_CONFIG = dedent("""
    receiver_email=jimmy@gmail.com # destination email address
    machine=Home NAS # description of this machine
    try_count=10 # number of tries to detect external ip
    ip_blacklist=192.168.*.*,10.*.*.* # external ips that are not allowed
""")

class InvalidConfigError(ValueError):
    def __init__(self, fname = None, missing = None):
        msg = "\n\nInvalid config file\n"
        if fname:
            msg += f"Could not read this file: {fname}\nPlease create it. "

        if missing:
            msg += f"Missing field: {missing}\n"

        msg += f"Example config file content:\n{EXAMPLE_CONFIG}"

        return super().__init__(msg)


@dataclasses.dataclass
class Config:
    receiver_email: str
    machine: str
    try_count: int = DEFAULT_TRY
    ip_blacklist: str = DEFAULT_BLACKLIST
    config_file: str = ""
    dry_run: bool = False

    @staticmethod
    def read(fname):
        logging.info("Reading %s", fname)

        try:
            with open(fname, "r") as f:
                content = f.read()

        except FileNotFoundError:
            raise InvalidConfigError(fname = fname)

        config = ConfigParser()
        config.read_string("[DEFAULT]\n" + content)
        config = config["DEFAULT"]

        if "machine" not in config:
            raise InvalidConfigError(field = "machine")

        if "receiver_email" not in config:
            raise InvalidConfigError(field = "receiver_email")

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
    for counter in range(try_count):

        # get an IP
        external_ip, local_ip, server = ipgetter.myip()

        # check to see that it has a ###.###.###.### format
        if not isipaddr(external_ip):
            logging.warning( "GetIP: Try %d:  Bad IP    (malformed): %s", counter + 1, external_ip)
            continue

        if isinblacklist(external_ip, blacklist):
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


logging.basicConfig(level=logging.DEBUG)

def main():
    # parse arguments
    import argparse
    import platformdirs


    default_config_file = platformdirs.user_config_path("ipwatch") / "config.txt"
    parser = argparse.ArgumentParser(description=f"""
This program gets for your external IP address
checks it against your "saved" IP address and,
if a difference is found, emails you the new IP.
This is useful for servers at residential locations
whose IP address may change periodically due to actions
by the ISP.

To be able to use it, create a config file
\"{default_config_file.absolute()}\"
with the folllowing info:\n{EXAMPLE_CONFIG}
""",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)

    parser.add_argument(
        "--config-file",
        default=default_config_file,
        help="read email-adresses, machine name, blacklist and try count from this file",
    )

    parser.add_argument("--dry-run", action="store_true", help="do not send email")

    args = parser.parse_args()

    # read config file
    config = Config.read(args.config_file)
    print(f"{config=}")

    save_ip_path = platformdirs.user_cache_path("ipwatch") / "saved_ip.txt"

    old_external_ip, old_local_ip = getoldips(save_ip_path)
    curr_external_ip, curr_local_ip, server = getips(
        int(config.try_count), config.ip_blacklist
    )

    # check to see if the IP address has changed
    if (curr_external_ip != old_external_ip) or (curr_local_ip != old_local_ip):
        # send email
        logging.info("Current IP differs from old IP.")
        sendmail(
            old_external_ip,
            old_local_ip,
            curr_external_ip,
            curr_local_ip,
            server,
            config.receiver_email,
            config.machine,
            dry_run = args.dry_run,
        )

        # updatefile
        updateoldips(save_ip_path, curr_external_ip, curr_local_ip)

    else:
        logging.info("Current IP = Old IP.  No need to send email.")


if __name__ == "__main__":
    main()
