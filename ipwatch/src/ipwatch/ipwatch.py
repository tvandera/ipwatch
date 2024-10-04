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

DEFAULT_TRY = 10
DEFAULT_BLACKLIST = "192.168.*.*,10.*.*.*"

@dataclasses.dataclass
class Config:
    email: str
    machine: str
    try_count: int = DEFAULT_TRY
    ip_blacklist: str = DEFAULT_BLACKLIST
    config_file: str = ""
    write_config_file: str = ""
    dry_run: bool = False

    @staticmethod
    def read(fname, **kwargs):
        logging.info("Reading %s", fname)
        config = ConfigParser()
        config.read(fname)
        config = config["DEFAULT"]
        values = { **config, **kwargs }
        return Config(**values)

    def write(self):
        if not self.write_config_file:
            return

        with open(self.write_config_file, 'w') as f:
            values = dataclasses.asdict(self)
            ConfigParser(values).write(f)

def isipaddr(ipstr):
    """True is ipstr matches x.x.x.x"""
    pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    return pattern.match(ipstr)


# return the current external IP address
def getips(try_count, blacklist):
    "Function to return the current, external, IP address"

    blacklist = blacklist.split(",")

    # try up to config.try_count servers for an IP
    for counter in range(try_count):

        # get an IP
        external_ip, local_ip, server = ipgetter.myip()

        # check to see that it has a ###.###.###.### format
        if not isipaddr(external_ip):
            logging.warning(
                "GetIP: Try %d:  Bad IP    (malformed): %s", counter + 1, external_ip
            )
            continue

        for black_ip in blacklist:
            if fnmatch(external_ip, black_ip):
                logging.warning(
                    "GetIP: Try %d:  Bad IP (in Blacklist): %s in %s",
                    counter + 1,
                    external_ip,
                    black_ip,
                )
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

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-file",
        dest="config_file",
        default=platformdirs.user_config_path("ipwatch") / "config.txt",
        help="read email-adresses, machine name, blacklist and try count from this file",
    )

    parser.add_argument("--write-config-file",  help="write config file")

    machine_arg = parser.add_argument("--machine",  help="use this as the machine name")
    email_arg  =parser.add_argument("--email", help="receiver email-adress")
    parser.add_argument("--try-count", type=int, default = DEFAULT_TRY, help="configure try count")
    parser.add_argument("--ip-blacklist", default = DEFAULT_BLACKLIST, help="configure black list")

    parser.add_argument("--dry-run", action="store_true", help="do not send email")

    args = parser.parse_args()

    # read config file
    config = Config.read(args.config_file, **vars(args))

    if not config.machine:
        raise argparse.ArgumentError(argument=machine_arg, message=f"Must specify machine name, either in config file ({args.config_file}), or on the command line")
    if not config.email:
        raise argparse.ArgumentError(argument=email_arg, message=f"Must specify email address(es), either in config file ({args.config_file}), or on the command line")

    config.write()

    save_ip_path = platformdirs.user_cache_path("ipwatch") / "saved_ip.txt"

    old_external_ip, old_local_ip = getoldips(save_ip_path)
    curr_external_ip, curr_local_ip, server = getips(
        config.try_count, config.ip_blacklist
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
