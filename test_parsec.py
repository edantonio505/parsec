import requests
import os

def saveFile(response, filename):
	with open(filename, 'wb') as f:
	    f.write(response.content)




def getIndexes():
	for year in range(2016, 1994, -1):
		for qtr in range(4, 0, -1):
			base_url = "https://www.sec.gov/Archives/edgar/full-index/{}/QTR{}/form.idx".format(year, qtr)
			response = requests.get(base_url)
			filename = "indexes/{}_{}_form.idx".format(year, qtr)

			if os.path.isfile(filename):
				print " {}_{}_form.idx already exists".format(year, qtr)
				pass
			else:
				print "saving {}_{}_form.idx".format(year, qtr)
				saveFile(response, filename)

		


def getCompanyFiles():
	cdir = "company_files"
	for file in os.listdir('indexes'):

		with open("indexes/{}".format(file),'r') as f:
			for line in f:
				r = line.split()
				if len(r) > 0:
					if r[0] == "10-Q" or r[0] == "4":
						indfile = r[-1]
						file_url = 'https://www.sec.gov/Archives/{}'.format(indfile)
						response = requests.get(file_url)
						new_filename = "{}/{}".format(cdir, indfile.split('/')[-1])


						if os.path.isfile(new_filename):
							print "{} already exists".format(new_filename)
							new_filename = "{}_{}.txt".format(new_filename.split('.')[0], indfile.split('/')[-2]) 

						print "saving {}".format(new_filename)
						saveFile(response, new_filename)









