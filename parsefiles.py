import os
from parsec import parsefile




directory = os.listdir('company_files')

# with open('company_files/AAPL_0001089355-02-000112.txt') as file:
# 	data = file.read()
# 	print parsefile(data)






for files in directory:
	with open('company_files/{}'.format(files)) as file:
		data = file.read()
		parsefile(data, files)