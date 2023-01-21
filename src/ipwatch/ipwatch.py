#!//usr/bin/env python3

#USAGE: python3 ipwatch.py [config]
#USAGE: ./ipwatch.py [config]
#
#[config] = path to an IPWatch configuration file
#
#Sean Begley
#2021-07-19
# v0.9
#
#This program gets for your external IP address
#checks it against your "saved" IP address and,
#if a difference is found, emails you the new IP.
#This is useful for servers at residential locations
#whose IP address may change periodically due to actions
#by the ISP.

#REFERENCES
#https://github.com/phoemur/ipgetter

from pathlib import Path
import re
import smtplib
from . import ipgetter
import subprocess
from dataclasses import dataclass
from textwrap import dedent
from configparser import ConfigParser
from collections import namedtuple


################
### CLASSES ####
################


def readconfig(fname):
    config = ConfigParser()
    config.read(fname)
    config = config['DEFAULT']
    Config = namedtuple('Config', config)
    return Config(**config)


def isipaddr(str):
    """ True is str matches x.x.x.x"""
    pattern = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    return pattern.match(str)

#return the current external IP address
def getips(try_count, blacklist):
    "Function to return the current, external, IP address"

    #try up to config.try_count servers for an IP
    for counter in range(int(try_count)):

        #get an IP
        external_ip, local_ip, server = ipgetter.myip()

        #check to see that it has a ###.###.###.### format
        if isipaddr(external_ip) and external_ip not in blacklist:
            print ("GetIP: Try %d: Good IP: %s" % (counter+1, external_ip))
            return external_ip, local_ip, server

        if external_ip in blacklist:
            print ("GetIP: Try %d:  Bad IP (in Blacklist): %s" % (counter+1, external_ip))
        else:
            print ("GetIP: Try %d:  Bad IP    (malformed): %s" % (counter+1, external_ip))

    raise ValueError("Could not get IPs")

#get old IP address
def getoldips(filepath):
    "Function to get the old ip address from savefile"
    #check if the savefile exists
    if not Path(filepath).is_file():
        return None, None

    with open(filepath, "r") as infile:
        old_external_ip, old_local_ip = [line.strip() for line in infile]
        assert isipaddr(old_external_ip) and isipaddr(old_local_ip)

    return old_external_ip, old_local_ip

#write the new IP address to file
def updateoldips(filepath,  new_external_ip, new_local_ip):
    "Function to update the old ip address from savefile"
    with open(filepath, "w") as savefile:
        savefile.write(new_external_ip)
        savefile.write("\n")
        savefile.write(new_local_ip)

#send mail with new IP address
def sendmail(old_exernal_ip, old_local_ip, new_external_ip, new_local_ip,
        server, receiver_emails,  machine):
    "Function to send an email with the new IP address"

    mailbody = dedent(f"""
     The IP address of {machine} has changed:
       Old external IP = {old_external_ip}
       Old local IP = {old_local_ip}
       New external IP: {new_external_ip}
       New local IP = {new_local_ip}
       The Server queried was {server}""")

    for email in receiver_emails:
        subprocess.check_output([ "/usr/bin/mail", "-s", f"new ip: {new_external_ip}", f"{email}"], input=mailbody, text=True)

################
##### MAIN #####
################

#parse arguments
config = readconfig("config.txt")

old_external_ip, old_local_ip = getoldips(config.save_ip_path)
curr_external_ip, curr_local_ip, server = getips(config.try_count, config.ip_blacklist)

#check to see if the IP address has changed
if ((curr_external_ip != old_external_ip) or (curr_local_ip != old_local_ip)):
    #send email
    print ("Current IP differs from old IP.")
    sendmail(
        old_external_ip, old_local_ip,
        curr_external_ip, curr_local_ip, server,
        config.receiver_email,
        config.machine)

    # updatefile
    updateoldips(config.save_ip_path,  curr_external_ip, curr_local_ip)

else:
    print ("Current IP = Old IP.  No need to send email.")



