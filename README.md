# ipwatch

Sean Begley (begleysm@gmail.com) [wiki](https://steamforge.net/wiki) [GitHub](https://github.com/begleysm/ipwatch)

2022-04-04

## Description

This program gets your external & internal IP addresses, checks them against
your "saved" IP addresses and, if a difference is found, emails you the new
IP's. This is useful for servers at residential locations whose IP address may
change periodically due to actions by the ISP.

## Usage

 `./ipwatch.py --help` will give you info on how to run ipwatch,
 where to create a config file, and an example content for this file.

## Installation

### Debian based Linux systems

Install python3, git, & nano by running

```bash
sudo apt install python3 git nano mailutils ssmtp
```

Clone the ipwatch repo by running

```bash
sudo git clone https://github.com/begleysm/ipwatch /opt/ipwatch
```

Copy `example_config.txt` to `config.txt` by running

```bash
sudo cp /opt/ipwatch/example_config.txt /opt/ipwatch/config.txt
```

Edit `config.txt` by running the following command and observing the
instructions in the **Config File** section below.

```bash
sudo nano /opt/ipwatch/config.txt
```

You can test the setup by running

```bash
sudo python3 /opt/ipwatch/ipwatch.py --dry-run --config-file /opt/ipwatch/config.txt
```

Check out the **Cronjob** section below to make this utility run on its own so that you may be quickly alerted to any IP changes on your system.

## Config File

ipwatch uses a config file to define how to send an email.  An example and
description is below.  A similar config file is in the repo as
example_config.txt.  You should copy it by running something like `sudo cp
example_config.txt config.txt` and then modify `config.txt`.

```dosini
# comma delimited list of the the email addresses of the recipients
receiver_email=tomreceiver@gmail.com, bobreceiver@gmail.com
#informative name of the machine
machine=Test_Machine
#how many times the system will try to find the current IP before exiting
try_count=10
#list of IP address to ignore if received
ip_blacklist=192.168.0.255,192.168.0.1,192.168.1.255,192.168.1.1
```

## Cronjob

ipwatch works best when setup as a cronjob.  For the following instructions I
assume that you've cloned the ipwatch repo into `/opt/ipwatch` and that your
config file is in the same location.  You can access root's crontab by running

```bash
sudo su
crontab -e
```

Below is an example crontab entry to run ipwatch once per hour.

```bash
00 * * * * /opt/ipwatch/ipwatch.py --config-file /opt/ipwatch/config.txt
```

## Configuring sending email

This repo contains an example `ssmtp` config file for sending email. See https://wiki.archlinux.org/title/SSMTP for more info.

If you use **2-Step Verification** with Gmail then you'll need configure your
Gmail account to **Sign in with App Passwords** which you can learn more about
by visiting https://support.google.com/accounts/answer/185833.

## Server List

The server list is hosted in this github repo as `servers.json`.  Locally, there
is a cached copy kept which will be re-retrieved from github every 90 days.

## References

The original ipgetter.py code came from https://github.com/phoemur/ipgetter.
However that repo is gone now.  This repo contains an updated copy of the
ipgetter.py file that has been modified to further support ipwatch.

## Thanks

1. Thanks to TheFlyingBadger for adding in support for the GitHub hosted servers.json file.
2. Thanks to pjuster for providing info on Gmail 2-Step Verification.
3. Thanks to carolmanderson for adding in support for monitoring local IP.
