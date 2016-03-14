#!/usr/bin/python2
# -*- coding: utf-8 -*-
#
# Copyright 2014 Peerchemist
#
# This file is part of Peerbox project.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
 
__author__ = "Peerchemist"
__license__ = "GPL"
__version__ = "0.5"

import os, sys
import sh
import argparse
import json
import urllib
import platform
import collections
import getpass
from node import Node
from health import Health
from datetime import timedelta
from datetime import datetime as dt

node = Node()
health = Health(node)

def system():
	'''parses system info'''

	def uptime():
		with open('/proc/uptime', 'r') as f:
			uptime_seconds = float(f.readline().split()[0])
			uptime_str = str(timedelta(seconds = uptime_seconds))

		return uptime_str

	def distr():
		return platform.linux_distribution()[0] + " " + platform.linux_distribution()[1]

	def temp():
		with open('/sys/class/thermal/thermal_zone0/temp', 'r') as temp:
			return(float(temp.readline().strip())/1000)

	mm = {
		'os': distr(),
		'uptime': uptime(),
		'avg_load': os.getloadavg()#,
		#'system_temperature': temp()
		}

	return mm

def hardware():
	'''parses hardware info'''

	info = {}

	with open('/proc/cpuinfo') as cpuinfo:
		for line in cpuinfo:
			if line.startswith('Hardware'):
				hardware = line.split(':')[1].strip()
				if hardware == "BCM2708":
					info['hardware'] = "Raspberry Pi_1"
				if hardware == "BCM2709":
					info["hardware"] = "Raspberry Pi_2"
			
			if line.startswith('Serial'):
				ser = line.split(':')[1].strip()
				info['serial'] = ser

	with open('/proc/cmdline', 'r') as cmdline:
		for i in cmdline.readline().split():
			if i.startswith('smsc95xx.macaddr'):
				info['macc'] = str(i.split('=')[1])

	return info

def isRunning():
	'''checks if ppcoind is running'''
	try:
		pid = sh.pidof("ppcoind").stdout.strip()
	except:
		return False

	if pid != None:
		return True

def exchangeRates():
	'''pull peercoin exchange rates from remote api'''

	api = "https://www.cryptonator.com/api/ticker/"
	try:
	  usd = json.loads(urllib.urlopen(api + "ppc-usd").read())["ticker"]["price"]
	  btc = json.loads(urllib.urlopen(api + "ppc-btc").read())["ticker"]["price"]
	except:
	  print("Can not connect to remote api")
	  return
	return {"usd": usd, "btc": btc}

def info(public=False):
	'''acts like just like ppcoind getinfo but on steroids'''

	info = node.getinfo()
	report = collections.OrderedDict()

	report["ppc_version"] = info["version"]
	report["os"] = system()["os"]
	report["hardware"] = hardware()["hardware"]
	if (public == False and "Raspberry Pi" in hardware()["hardware"]):
	  report["serial"] = hardware()["serial"]
	  report["macc addr"] = hardware()["macc"]
	report["uptime"] = system()["uptime"]
	#report["average_load"] = system()["avg_load"]
	
	if public == False:
		report["balance"] = info["balance"]
		if (int(report["balance"]) != 0 
		    and exchangeRates() != None
		    and info["testnet"] == False):
		  report["value"] = {"BTC": int(float(report["balance"]) * float(exchangeRates()["btc"])),
		                      "USD": int(float(report["balance"]) * float(exchangeRates()["usd"]))}
		report["stake"] = info["stake"]
		report["newmint"] = info["newmint"]
	
	if public == False:
	  report["ip"] = info["ip"]
	report["connections"] = info["connections"]
	report["blocks"] = info["blocks"]
	report["moneysupply"] = info["moneysupply"]
	report["pos_difficulty"] = node.getdifficulty()["proof-of-stake"]
	report["pow_difficulty"] = node.getdifficulty()["proof-of-work"]
	
	if info["testnet"] == True:
		report["testnet"] = True

	report["protocolversion"] = info["protocolversion"]
	report["walletversion"] = info["walletversion"]

	return report

def healthCheck():
	'''compares local blockchain data with ppc.blockr.io as reference point'''

	report = health.check()
	print
	print "Checking if we are on the right chain..."
	print "Using" + " " + "ppc.blockr.io" + " as reference."
	print

	for k,v in report.items():
		if v == True:
			print(k + ":" + " True")
		else:
			print(k + ":" + " False")

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description='Show information on Peerbox.')
	parser.add_argument('-info', help='''equal to "ppcoind getinfo" with some extras''', action="store_true")
	parser.add_argument("-public", help="show info with omitted private data", action="store_true")
	parser.add_argument('-stdout', help='dump data to stdout, use to pipe to some other program', action="store_true")
	parser.add_argument('-health', help='compare local blockchain data with ppc.blockr.io as reference', action="store_true")
	parser.add_argument("-rates", help="current average PPC exchange rates in USD and BTC", action="store_true")
	parser.add_argument("-start", help="start Peerbox", action="store_true")
	parser.add_argument("-stop", help="stop Peerbox", action="store_true")
	parser.add_argument("-restart", help="restart Peerbox", action="store_true")
	args = parser.parse_args()

if isRunning() == False and not args.start:
	print('''Peerbox is not running. Please start Peerbox with "peerbox -start" ''')
	sys.exit()

if isRunning() == False and args.start:
	print("Staring Peerbox...")
	sh.sudo("systemctl", "start", "ppcoind@{0}.service".format(getpass.getuser()))
	sys.exit()

if isRunning() == True and args.start:
	print("Peerbox is already running.")
	
if args.restart:
	sh.sudo("systemctl", "restart", "ppcoind@{0}.service".format(getpass.getuser()))

if args.stop:
	sh.sudo("systemctl", "stop", "ppcoind@{0}.service".format(getpass.getuser()))

if args.info:
	print(json.dumps(info(), indent=4))

if args.public:
	print(json.dumps(info(public=True), indent=4))

if args.stdout:
	sys.stdout.write(info())

if args.health:
	healthCheck()

if args.rates:
	print(json.dumps(exchangeRates(), indent=4))

if not any(vars(args).values()) == True:
	print(json.dumps(info(), indent=4))