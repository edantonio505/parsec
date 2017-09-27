import requests
import os
import sys
import time
import bisect


def getCurrentQuarter():
	current_year = int(time.strftime("%Y"))
	quarters = range(1, 12, 3)         
	month = int(time.strftime("%m"))
	current_quarter = bisect.bisect(quarters, month)
	return current_quarter, current_year


def saveFile(response, filename):
	with open(filename, 'wb') as f:
	    f.write(response.content)




def saveIndexFile(year, qtr):
	base_url = "https://www.sec.gov/Archives/edgar/full-index/{}/QTR{}/form.idx"
	filename = "indexes/{}_{}_form.idx"
	response = requests.get(base_url.format(year, qtr))
	print "saving {}_{}_form.idx".format(year, qtr)
	saveFile(response, filename.format(year, qtr))



def getIndexes(get_current = False):
	current_quarter, current_year = getCurrentQuarter()
	if get_current == True:
		print "updating current quarter index"
		saveIndexFile(current_year, current_quarter)
	else:
		for year in range(current_year, 1994, -1):
			for qtr in range(4, 0, -1):
				if qtr > current_quarter and year == current_year:
					pass
				else:
					if os.path.isfile("indexes/{}_{}_form.idx".format(year, qtr)):
						print " {}_{}_form.idx already exists".format(year, qtr)
						pass
					else:
						saveIndexFile(year, qtr)

		


def getCompanyFiles(cik, company_ticker):
	cdir = "company_files"
	cik = str(cik)
	for file in os.listdir('indexes'):
		with open("indexes/{}".format(file),'r') as f:
			print "checking {}".format(file)
			for line in f:
				r = line.split()
				if len(r) >= 5:
					if cik == r[-3]:
						indfile = r[-1]
						file_url = 'https://www.sec.gov/Archives/{}'.format(indfile)
						response = requests.get(file_url)
						new_filename = "{}/{}_{}".format(cdir, company_ticker ,indfile.split('/')[-1])

						if os.path.isfile(new_filename):
							print "{} already exists".format(new_filename)
							# new_filename = "{}_{}.txt".format(new_filename.split('.')[0], indfile.split('/')[-2]) 
						else:
							print "saving {}".format(new_filename)
							saveFile(response, new_filename)





def getSecFilesFromTickers(ptickers):
	import pandas as pd
	if ptickers == None or len(ptickers) < 1:
		print "No tickers provided, please provide some"
		exit()

	for company_ticker in ptickers:
		tickers = pd.read_csv('cik_ticker.csv', sep='|')
		company = tickers[tickers['Ticker'] == company_ticker]
		if company.shape[0] > 0:
			print "Getting files from {}".format(company.Name.values[0])
			cik = company.CIK.values[0]
			print "cik {}".format(cik)
			getCompanyFiles(cik, company_ticker)
		else:
			print "{} does not exist in company tickers cik file".format(company_ticker)




def getSecFiles(ptickers = None):
	if len(os.listdir('indexes')) >= 88:
		getIndexes(get_current = True)
		getSecFilesFromTickers(ptickers)
	else:
		getIndexes()
		getSecFilesFromTickers(ptickers)


possible_tickers = ['AAPL', 'B', 'F', 'FB', 'GOOGL']
getSecFiles(possible_tickers)
