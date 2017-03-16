## import all necessary modules
import mechanize
from bs4 import BeautifulSoup
import pandas as pd

debug = True

## intantiate an empty dataframe with name and id
df = pd.DataFrame(columns = ['research_id', 'research_name'])

## intatiate mechanize browser, read the response and pass it to soup
br = mechanize.Browser()
url = 'http://www.nist.gov/publication-portal.cfm'
br.open(url)

if debug:
    print 'Successfully opened the publication portal page'
    print ''
    print 'Extracting the research id, name pairs'

html = br.response().read()
soup = BeautifulSoup(html, 'lxml')

if debug:
    print 'Successfully read response of the publication portal page and passed to BS'

## the name and ids are found in an element with id researchfield
researchfield = soup.find(attrs = {'id':'researchfield'})

## get all the select options, iterate through them and get the id and name
options = researchfield.findAll('option')
for option in options:
    nrows = df.shape[0]
    df.loc[nrows+1] = [option['value'], option.getText()]
    if debug:
        print option['value'], ' : ', option.getText()

## export the dataframe to a csv
df.to_csv('research_name_ids.csv', index = False, encoding = 'utf-8')

if debug:
    print 'Successfully exported the name id to file'
