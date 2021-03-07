#!/usr/bin/env python3
import time
import os
import sys
import platform
import requests
import pycurl
import re
import ssl
import warnings
import json

ver = platform.python_version()

recce_version = '3.3'

slack_webhook = "PUT HERE(DONT REMOVE QUOTES)"				#slack_webhook_URL

if (ver <= '3'):
        print("\033[91m Recce isn't compatible with python2 use python 3.x\033[00m")
        sys.exit(1)

import argparse
import concurrent.futures

parser = argparse.ArgumentParser(description="""\033[93m[~] Domain status checker by shubham chaskar
									https://twitter.com/chaskar_shubham\033[00m""")

group = parser.add_mutually_exclusive_group()

group1 = parser.add_mutually_exclusive_group()

group2 = parser.add_mutually_exclusive_group()
												#Taking arguments from CLI
parser.add_argument("-v","--verbose", help="verbose",action="store_true")

group1.add_argument("-o","--output", help="write active domains in new file" ,metavar="out-file")

group1.add_argument("-c","--csv", help="mention .csv file to write output",metavar="csv-file")

parser.add_argument("-t","--threads", help="number of concurrent threads" ,type=int,metavar="Threads")

group.add_argument("-f","--file", help="File which consist domains(sub.example.com)",metavar="Input file")

group.add_argument("-d","--domain", help="single domain check",metavar="domain")

group2.add_argument("-s","--server",help="print web server",action="store_true")

parser.add_argument("-u","--update",help="update recce",action="store_true")

group2.add_argument("-l","--live",help="only print live subdomains",action="store_true")

parser.add_argument("-r","--length",help="print response length",action="store_true")

parser.add_argument("-F","--follow",help="Follow redirect",action="store_true")

parser.add_argument("-S","--slack",help="send slack notification",action="store_true")

args = parser.parse_args()

verbose = args.verbose
file = args.file
domain_name = args.domain
output = args.output
threads = args.threads
server = args.server
live = args.live
csv = args.csv
length = args.length
update = args.update
follow = args.follow
slack = args.slack
print("""\033[91m
.______       _______   ______   ______  _______
|   _  \     |   ____| /      | /      ||   ____|
|  |_)  |    |  |__   |  ,----'|  ,----'|  |__
|      /     |   __|  |  |     |  |     |   __|
|  |\  \----.|  |____ |  `----.|  `----.|  |____
| _| `._____||_______| \______| \______||_______|\033[00m

					\033[93m v"""+recce_version+""" By shubham_chaskar\033[00m
""")

warnings.filterwarnings('ignore')
ssl._create_default_https_context = ssl._create_unverified_context


if not threads:										#default number of threads
	threads = 20
if csv:
	if not csv.endswith(".csv"):
		print("\033[91m[!]Your file must end with .csv extension\033[00m")
		sys.exit(1)
try:
	from io import BytesIO
except ImportError:
	from StringIO import StringIO as BytesIO


def updater():

	res = requests.get("https://raw.githubusercontent.com/unstabl3/recce/master/recce.py").text

	r2 = re.search(r"recce_version = '(.*)'",res)

	new_match = str(r2.group())

	new_version = re.search(r"\d+\.\d+", new_match).group()

	if new_version > recce_version:

		print("\033[93m[~]Update available for recce and Download is in progress.\033[00m")

		current_directory = os.getcwd()

		new_folder = current_directory.split("/")[-1]

		try:

			os.system('git clone --quiet https://github.com/unstabl3/recce.git %s' % (new_folder))

			os.system('cp -r %s/%s/* %s' % (current_directory,new_folder,current_directory))

			os.system('rm -rf %s/%s/' % (current_directory,new_folder))

			print("\033[91m[!] Successfully updated..")

		except Exception as ex:

			print("\033[91m[!]Error ",ex,"\033[00m")

	else:
		print("\033[91m[!]Recce is already in his latest version\033[00m")

		sys.exit(0)

if update:
	updater()
	sys.exit(0)

headers = {}
redirect = []
csv_list = []
live_domains = []

if verbose:
	print("\033[93m[~] Verbosity is enabled..\033[00m")

def slack_Noti(data):

	webhook = slack_webhook
	slack_data = {'text':data}
	response = requests.post(webhook,data=json.dumps(slack_data),headers={'Content-Type':'application/json'})

	if not response.status_code == 200:
		raise ValueError('some error %s %s' %(response.status_code, response.text))

	else:
		print("Data sent successfully..")
		print("Executor is now releasing resources..")

def header_function(header_line):

	header_line = header_line.decode('iso-8859-1')

	if ':' not in header_line:
		return

	name, value = header_line.split(':', 1)

	name = name.strip()

	value = value.strip()

	name = name.lower()

	headers[name] = value

def csv_output(csv_list):

	csv_file = ''

	if server:
		if length:
			csv_file += 'Domain,Status_code,Server_name,Response_length\n'
		else:
			csv_file += 'Domain,Status_code,Server_name\n'

	else:
		csv_file += 'Domain,Status_code\n'

	for item in csv_list:
		csv_file += item + '\n'
	report = csv_file
	try:
		with open(csv, 'a') as f:

			f.write(report)

		f.close()

		print("\033[93m[!]File saved\033[00m")

	except Exception as ex:
		print(ex)


def recce(domain):

	buffer = BytesIO()

	req = pycurl.Curl()

	req.setopt(pycurl.URL, domain)

	req.setopt(req.NOBODY, True)

	req.setopt(req.FOLLOWLOCATION, True)

	req.setopt(pycurl.HEADERFUNCTION, header_function)

	req.setopt(req.WRITEDATA, buffer)

	try:
		req.perform()
	except:
		pass

	result = req.getinfo(req.RESPONSE_CODE)

	if follow:
		if 'location' in headers:

			url = str(headers['location'])

			redirect.append(url)

	if live:

		if not result == 0:
			if verbose:
				print("\033[92m",domain.strip(),"\033[00m",":",result)
			else:
				print("\033[92m",domain.strip(),"\033[00m")
			if output:
				with open(output,"a") as output_file:
					output_file.write(domain + "\n")
			else:
				live_domains.append(domain)
	return result


def server_check(domain):

	buffer = BytesIO()

	ser = pycurl.Curl()

	ser.setopt(pycurl.URL, domain)

	ser.setopt(ser.FOLLOWLOCATION, True)

	ser.setopt(pycurl.HEADERFUNCTION, header_function)

	ser.setopt(ser.WRITEDATA, buffer)

	try:
		ser.perform()
	except:
		pass

	if 'server' in headers:

		try:
			if 'content-length' in headers:

				return str(headers['server']),str(headers['content-length'])

		except:
			return str(headers['server']),str("None")

def check(data,domain):
												#This function will compare result
	if (data == 0):

		print("\033[91m[~]Domain name: " , domain)

		print("[!]Status: \tDown\033[00m")

		print("-" * 150)
	else:

		if verbose:

			print("\033[92m[~]Domain name: " , domain)

			print("[!]Status: \t live")

			print("[@]Response: \t",data)

			if server:
				server_name,c_length = server_check(domain)

				print("[$]Server: \t",server_name,"\033[00m")

				if length:

					print("\033[92m[#]Length: \t",c_length,"\033[00m")

			print("-" * 150)

		else:
			if server:
				server_name,c_length = server_check(domain)

				print("\033[92m[~]Domain name: " , domain)

				print("[!]Status: \t live")

				print("[$]Server: \t",server_name,"\033[00m")

				if length:

					print("\033[92m[#]Length: \t",c_length,"\033[00m")

				print("-" * 150)

			else:
				print("\033[92m[~]Domain name: " , domain)

				print("[!]Status: \t live\033[00m")

				print("-" * 150)

		if output:
			with open(output,"a") as output_file:						#Writing output to new file

				output_file.write(domain + "\n")
		else:
			live_domains.append(domain)
		if csv:
			if server:
				if length:
					csv_list.append(str(domain) + "," + str(data) + "," + str(server_name) + "," + str(c_length))
				else:
					csv_list.append(str(domain) + "," + str(data) + "," + str(server_name))
			else:
				csv_list.append(str(domain) + "," + str(data))


if file:

	if os.path.isfile(file):
		num_domains = 0

		with open(file,"r") as f:
			for domain in f:
				num_domains += 1
		f.close()

		print("\033[92m[~] Total number of domains found in the file are: ", num_domains,"\033[00m")


		with open(file,"r") as f:

			pool = concurrent.futures.ThreadPoolExecutor(max_workers=threads)

		#Start the load operations and mark each future with its domain

			futures = {pool.submit(recce,domain.strip()):domain for domain in f}

			try:
				for future in concurrent.futures.as_completed(futures,timeout=5):
					domain = futures[future]

					try:
						data = future.result(timeout=2)
						if not live:
							check(data,domain.strip())
					except concurrent.futures.TimeoutError:
						pass
					except Exception as exc:

						print('%r generated an exception: %s' % (domain, exc))
			except concurrent.futures.TimeoutError:
				pass
	else:
		print("\033[91m[!] File not found..\033[00m")
		sys.exit(1)

if "-f" in sys.argv:
	pass
else:
	pool = concurrent.futures.ThreadPoolExecutor(max_workers=threads)
	futures = {pool.submit(recce,domain.strip("\n")):domain for domain in sys.stdin}

	try:
		for future in concurrent.futures.as_completed(futures,timeout=5):
			domain = futures[future]

			try:
				data = future.result(timeout=2)
				if not live:
					check:(data,domain.strip())
			except concurrent.futures.TimeoutError:
				pass
			except Exception as exc:
				print("%r generated an exception: %s" % (domain, exc))

	except concurrent.futures.TimeoutError:
		pass

if domain_name:													#For single domain check

	data = recce(domain_name)

	check(data,domain_name)

if follow:
	redirects = list(dict.fromkeys(redirect))
	if not len(redirect) == 0:

		print("\033[93m*" * 150)
		print("*" * 150)
		print("[~]Redirect urls found")
		print("\033[93m*" * 150)
		print("*" * 150,"\033[00m")

		pool = concurrent.futures.ThreadPoolExecutor(max_workers=20)

		futures = {pool.submit(recce,domain.strip()):domain for domain in redirects}

		try:
			for future in concurrent.futures.as_completed(futures,timeout=5):
				domain = futures[future]

				try:
					data = future.result(timeout=2)
					if not live:
						check(data,domain.strip())
				except Exception as ex:
					print(ex)

		except concurrent.futures.TimeoutError:
			pass
if csv:
	csv_output(csv_list)
time.sleep(8)
if slack:
	if output:
		live_domains = 0
		with open(output,"r") as r:
			for domain in r:
				live_domains += 1

			data = "%s:skull: Recce completed the scan.." % ("<!channel> ")
			slack_Noti(data)
			data = "[~] Total Live domains are: %d." % (live_domains)
			slack_Noti(data)
	else:
		data = "%s:skull: Recce completed the scan.." % ("<!channel> ")
		slack_Noti(data)
		data = "[~] Total Live domains are: %d." % (len(live_domains))
		slack_Noti(data)


else:
	print("Executor is now releasing the resources..")
