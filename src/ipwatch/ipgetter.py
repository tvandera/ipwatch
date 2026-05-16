"""
This module is designed to fetch your external IP address from the internet.
It is used mostly when behind a NAT.
It picks your IP randomly from a server list to minimize request
overhead on a single server


API Usage
=========

    >>> import ipgetter
    >>> myip = ipgetter.myip()
    >>> myip
    '8.8.8.8'

    >>> ipgetter.IPgetter().test()

    Number of servers: 47
    IP's :
    8.8.8.8 = 47 ocurrencies


Copyright 2014 phoemur@gmail.com
This work is free. You can redistribute it and/or modify it under the
terms of the Do What The Fuck You Want To Public License, Version 2,
as published by Sam Hocevar. See http://www.wtfpl.net/ for more details.

Updated by Sean Begley for the ipwatch project (https://github.com/begleysm/ipwatch/)
"""

import http.cookiejar as cjar
import importlib.resources
import json
import os
import random
import re
import socket
import ssl
import urllib.request as urllib
from fnmatch import fnmatch

__version__ = "0.7"


BLACKLIST = ["192.168.*.*","10.*.*.*","127.*.*.*"]

def isinblacklist(ip, blacklist = BLACKLIST):
    for black_ip in blacklist:
        if fnmatch(ip, black_ip):
            return True

    return False

def myip():
    return IPgetter().get_ips()

class ServerList:
    def __init__(self, file = None):
        if file:
            self.server_list = self.from_file(file)
        else:
            self.server_list = self.builtin()

    def __getitem__(self, index):
        return self.server_list[index]

    def __iter__(self):
        return iter(self.server_list)

    def __len__(self):
         return len(self.server_list)

    def builtin(self):
        from . import data
        builtin = importlib.resources.files(data) / 'servers.json'
        with builtin.open("rt") as f:
            data = f.read()
            return json.loads(data)

    def from_file(self, file):
        with open(file) as f:
            data = f.read().decode("utf-8")
            return json.loads(data)

class IPgetter:
    """
    This class is designed to fetch your external IP address from the internet.
    It is used mostly when behind a NAT.
    It picks your IP randomly from a server_list to minimize request overhead
    on a single server
    """
    def __init__(self, server_list = None):
        self.server_list = server_list if server_list else ServerList()

    def get_externalip(self):
        """
        This function gets your IP from a random server
        """

        myip = ""
        for _ in range(7):
            server = random.choice(self.server_list)
            myip = self.fetch(server)
            if myip != "":
                break
        return myip, server

    def get_local_ip(self):
        # From https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def get_ips(self):
        local_ip = self.get_local_ip()
        external_ip, server = self.get_externalip()
        return external_ip, local_ip, server

    def fetch(self, server):
        """
        This function gets your IP from a specific server.
        """
        url = None
        cj = cjar.CookieJar()
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        opener = urllib.build_opener(
            urllib.HTTPCookieProcessor(cj), urllib.HTTPSHandler(context=ctx)
        )
        opener.addheaders = [
            (
                "User-agent",
                "Mozilla/5.0 (X11; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0",
            ),
            (
                "Accept",
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            ),
            ("Accept-Language", "en-US,en;q=0.5"),
        ]

        try:
            url = opener.open(server, timeout=4)
            content = url.read()

            # Didn't want to import chardet. Prefered to stick to stdlib
            try:
                content = content.decode("UTF-8")
            except UnicodeDecodeError:
                content = content.decode("ISO-8859-1")

            m = re.search(
                r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)",
                content,
            )
            myip = m.group(0)
            return myip if len(myip) > 0 else ""
        except Exception:
            return ""
        finally:
            if url:
                url.close()

    def test(self):
        """
        This functions tests the consistency of the servers
        on the list when retrieving your IP.
        All results should be the same.
        """

        from collections import Counter

        resultdict = {
            server : self.fetch(server)
            for server in ServerList()
        }

        print("Number of servers: ", len(self.server_list))
        print("IP's :", Counter(resultdict.values()))
        print("Full result: ", resultdict)

        print("Empty IPs: ", [server for server, ip in resultdict.items() if ip == ''])

        valid_ips = set(r for r in resultdict.values() if r != '')
        assert(len(valid_ips) >= 1)
        print("In blacklist: ", [server for server, ip in resultdict.items() if isinblacklist(ip, BLACKLIST)])

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", help ="tests the consistency of the servers")

    args = parser.parse_args()
    if args.verify:
        IPgetter().test()
    else:
        print(myip())
