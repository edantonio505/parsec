import requests
import bs4
import json
import re
import string
import datetime
import sys
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import pandas as pd

def getIndex(year, qtr):
	base_url = "https://www.sec.gov/Archives/edgar/full-index/"
	full_url = base_url + str(year) + "/QTR" + str(qtr) + "/form.idx"
	
	data  = requests.get(full_url).content
	lines = data.split('\n')

	index = []
	for i in range(len(lines)):
		items = lines[i].split()
		if len(items) > 0 and items[0] == "10-Q":
			last = len(items) - 1

			company = ""
			for n in range(1, last - 3):
				company += " " + items[n]
			company = company[1:].lower()
			if company.endswith(','): company = company[:-1]

			cik      = items[last - 2]
			date     = items[last - 1]
			filename = items[last]
			
			row = {"company": company, "cik": cik, "date": date, "filename": filename}
			index.append(row)
	return index





def cleanText(dirty):
	if isinstance(dirty, basestring):
		clean = dirty.strip(string.whitespace).strip(u'\xa0').encode('ascii', 'ignore').replace("'", "").lower()
		clean = " ".join(clean.split())
		if len(clean) > 0: return clean
		else: return False
	else: return False





def cleanNumber(dirty):
	if isinstance(dirty, basestring):
		dirty = dirty.replace(',', '')
		clean = re.search('\(?\d+\.?\d*\)?', dirty)
		if clean:
			clean = clean.group(0)
			number = re.search('\d+\.?\d*', clean)
			if number:
				number = float(number.group(0))
				if clean[0] == '(' or clean[-1] == ')': number *= -1
				return number
		else: return False
	else: return False





def matchHeader(text, data):
	for header in data:
		for accepted in header['accepted']:
			if text == accepted:
				return header['header']
	return False





def compareValues(v1, v2, t1, t2):
	if (v1 - v2) >= t1 and (v1 / (float(v2) + 0.1)) >= t2: return True
	else: return False





def findUnits(page):
	cnt_thou = len(re.findall('thousands', page, re.IGNORECASE))
	cnt_mill = len(re.findall('millions', page, re.IGNORECASE))

	if   compareValues(cnt_thou, cnt_mill, 3, 3): return 1
	elif compareValues(cnt_mill, cnt_thou, 3, 3): return 1000
	elif (cnt_thou + cnt_mill) <= 3:       return 0.001
	else: return False





def getRows(page, soup):
	tables = soup.findAll('table')

	if tables:
		all_rows = []
		for table in tables:
			rows = table.findAll('tr')
			if not rows:
				rows = table.text.split('\n')
			all_rows.extend(rows)
		return all_rows
	else:
		return page.split('\n')





def findDateOrder(row):
	dates = []
	
	if hasattr(row, 'findAll'):
		cells = row.findAll('td')
		if not cells: 
			cells = row.text.split('   ')
	else: cells = row.split('   ')
	
	if cells:
		if len(cells) > 1:
			for cell in cells:
				if hasattr(cell, 'text'): text = cleanText(cell.text)
				else: text = cleanText(cell)
				if text:
					date_str = re.search('\w+ \d\d?, \d\d\d\d', text)
					if not date_str:
						date_str = re.search('\d\d\d\d', text)
					if date_str:
						try: date = datetime.datetime.strptime(date_str.group(0), '%B %d, %Y')
						except ValueError:
							try: date = datetime.datetime.strptime(date_str.group(0), '%Y')
							except ValueError: date = False
						if date: 
							date_min = datetime.datetime.strptime('1990', '%Y')
							date_max = datetime.datetime.today() + datetime.timedelta(weeks=52)
							if date > date_min and date < date_max:
								dates.append(date)
		if len(dates) == 2 or len(dates) == 4:
			if dates[0] > dates[1]: return 'std'
			else: return 'rev'
		else: return False
	else: return False





def setDateOrder(rows):
	cnt_std = 0
	cnt_rev = 0
	for row in rows:
		order = findDateOrder(row)
		if order:
			if   order == 'std': cnt_std += 1
			elif order == 'rev': cnt_rev += 1

	if   compareValues(cnt_std, cnt_rev, 2, 5): return 'std'
	elif compareValues(cnt_rev, cnt_std, 2, 5): return 'rev'
	else: return 'std'





def parseRow(row, data, units, date_order):
	values = []
	
	if hasattr(row, 'findAll'):
		cells = row.findAll('td')
		if not cells: 
			cells = row.text.split('   ')
	else: cells = row.split('   ')

	if cells:
		if len(cells) > 1:
			if hasattr(cells[0], 'text'):
				text = cleanText(cells[0].text)
			else: text = cleanText(cells[0])

			header = matchHeader(text, data)
			if header:
				for i in range(1, len(cells)):
					if hasattr(cells[i], 'text'):
						value = cleanNumber(cells[i].text)
					else: value = cleanNumber(cells[i])
					if value:
						if "share" in header: values.append(value)
						else: values.append(float(value * units))
				
				if len(values) == 2 or len(values) == 4:
					if   date_order == 'std': output = values[0::2]
					elif date_order == 'rev': output = values[1::2]
					else: output = False

					if output:
						if len(output) == 1: output = output[0]
						return {'header': header, 'values': output}
					else: return False
				else: return False 
			else: return False
		else: return False
	else: return False





def resetValues(data):
	for i in range(len(data)):
		for j in range(len(data[i]['values'])):
			data[i]['values'][j] = 0
	return data





def valuesFilled(data):
	flag    = True
	missing = []

	for item in data:
		if not item['optional']:
			if item['values'] == 0: 
				flag = False
				missing.append(item['header'])
	return {'success': flag, 'missing': missing}





def parseReportSection(data, rows, units, date_order):
	fails = 0
	done  = False
	for row in rows:
		if not done:
			output = parseRow(row, data, units, date_order)
			if output: 
				for i in range(len(data)):
					if data[i]['header'] == output['header']:
							if data[i]['values'] == 0: data[i]['values'] = output['values']
			else: fails += 1
	return data





def slimData(data):
	output = []
	for item in data:
		row = {'header': item['header'], 'values': item['values']}
		output.append(row)
	return output





def parseReport(rows, units, date_order):
	with open('headers.json') as headers_json:
		headers = json.load(headers_json)
	output  = []
	errors  = []
	success = True
	
	for section in headers:
		parsed = parseReportSection(section['data'], rows, units, date_order)
		validate = valuesFilled(parsed)
		if validate['success']:
			output += slimData(parsed)
		else: 
			success = False
			error   = {'*section': section['table'], 'missing': validate['missing']}
			errors.append(error)
	return {'success': success, 'output': output, 'errors': errors}





def parsec(filename, info):
	success = False
	errors  = []
	output  = []

	base_url = 'https://www.sec.gov/Archives/'
	
	updateStatus(info, 'Downloading report...')
	page    = requests.get(base_url + filename).content
	pg_tags = page.count('<')
	updateStatus(info, 'Download complete. Parsing HTML...')

	if pg_tags < 500000:
		soup = bs4.BeautifulSoup(page, "lxml")
		units = findUnits(page)
		
		if units:
			rows = getRows(page, soup)
			date_order = setDateOrder(rows)
			
			if date_order:
				updateStatus(info, 'Parsing complete. Searching financial data...')
				data = parseReport(rows, units, date_order)
				if data['success']:
					success = True
					output  = data['output'] 
				else: 
					errors.append('Report parse failure')
					errors.append(data['errors'])
			else: errors.append('Date order not found') 
		else: errors.append('Units not found')
	else: errors.append('Report too long')

	return {'success': success, 'output': output, 'errors': errors}









def parsefile(page, file):
	if "<?xml" in page:
		thing = BeautifulSoup(page, "lxml")

		xml = thing.findAll('xml')

		if len(xml) > 0:
			root = ET.fromstring(str(xml[0])[6:-6])
			all_records = []
			for child in root:
				if len(child) < 1:
					print "{}: {}".format(child.tag, child.text)
				else:
					print child.tag
					for subchild in child:
						if len(subchild) < 1:
							print "|-- {}: {}".format(subchild.tag, subchild.text)
						else:
							print "|-- {}".format(subchild.tag) 
							for x in subchild:

								if len(x) < 1:
									print "|--|-- {}: {}".format(x.tag, x.text)
								else:
									print "|--|-- {}".format(x.tag)
									for i in x:
										if len(i) < 1:
											print "|--|--|-- {}: {}".format(i.tag, i.text)
										else:
											print "|--|--|-- {}".format(i.tag)
											for a in i:
												print "|--|--|--|-- {}: {}".format(a.tag, a.text)
		else:
			print "something wrong with XML"
			print xml
			print file
			exit()			

	# return {'success': success, 'output': output, 'errors': errors}






def updateStatus(info, status):
	valid   = info['valid']
	total   = info['total']
	if total == 0: total = 1
	pvalid  = int((float(valid) / total) * 100)

	start   = info['start']
	now     = datetime.datetime.now()
	elapsed = now - start
	runtime = elapsed.total_seconds() / total
	perday  = 86400 / float(runtime) / 1000

	cik     = info['cik']
	date    = info['date']

	update  = str(valid) + '/' + str(total) + ' ' + str(pvalid) + '%' + ' Successful; ' + str(round(perday, 1)) + 'k/day; CIK ' + cik + '; Report ' + date + '; ' + now.strftime("%d %b %I:%M:%S%p") + ' ' + status + ' '*30 
	sys.stdout.write('\r')
	sys.stdout.write(update)
	sys.stdout.flush()