## import all modules
import json, requests, pyPdf, sys, os
from newspaper import Article
from bs4 import BeautifulSoup
from pyPdf import PdfFileReader
import dateutil.parser as dparser
from text_unidecode import unidecode

## Step1 - retrieve basic info on all prize winners. Ids will be used
## to get more detailed info
url = 'http://api.nobelprize.org/v1/prize.json'
resp = requests.get(url)
data = json.loads(resp.text)
l = len(data['prizes'])
os.chdir(os.path.dirname(os.path.realpath(__file__)))

def readPDF(filename):
    """Function to read the attachment and return the contents"""
    input = PdfFileReader(file(filename, "rb"))
    content = ''
    for page in input.pages:
        content += ' ' + page.extractText()
    return content
    
def download_file(url):
    """ function to download the files to local"""
    local_filename = url.split('/')[-1]
    r = requests.get(url, stream=True)
    with open(local_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024): 
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
    return local_filename

for i in range(l):
    """Iterate through all the prizes"""
    category = data['prizes'][i]['category']
    if category == 'economics':
        category = 'economic-sciences'
    year = data['prizes'][i]['year']
    num_laureates = len(data['prizes'][i]['laureates'])
    for j in range(num_laureates):
        try:
            share = data['prizes'][i]['laureates'][j]['share']
        except:
            share = ''
        try:
            motivation = data['prizes'][i]['laureates'][j]['motivation']
        except:
            motivation = ''
        try:
            surname = data['prizes'][i]['laureates'][j]['surname']
        except:
            surname = ''
        id = data['prizes'][i]['laureates'][j]['id']
        try:
            firstname = data['prizes'][i]['laureates'][j]['firstname']
        except:
            firstname = ''

        laureate_uri = 'http://api.nobelprize.org/v1/laureate.json?id='+str(id)
        response = requests.get(laureate_uri)
        laureate_data = json.loads(response.text)
        try:
            gender = laureate_data[u'laureates'][0]['gender']
        except:
            gender = ''
        try:
            diedCity = laureate_data[u'laureates'][0]['diedCity']
        except:
            diedCity = ''
        try:
            diedCountryCode = laureate_data[u'laureates'][0]['diedCountryCode']
        except:
            diedCountryCode = ''
        try:
            diedCountry = laureate_data[u'laureates'][0]['diedCountry']
        except:
            diedCountry = ''
        try:
            born = laureate_data[u'laureates'][0]['born']
        except:
            born = ''
        try:
            bornCountry = laureate_data[u'laureates'][0]['bornCountry']
        except:
            bornCountry = ''
        try:
            bornCity = laureate_data[u'laureates'][0]['bornCity']
        except:
            bornCity = ''
        try:
            affiliations = laureate_data[u'laureates'][0]['prizes'][0]['affiliations']
        except:
            affiliations = ''
        try:
            motivation = laureate_data[u'laureates'][0]['prizes'][0]['motivation']
        except:
            motivation = ''
        try:
            died = laureate_data[u'laureates'][0]['died']
            if died=='0000-00-00':
                died = ''
        except:
            died = ''
        try:
            bornCountryCode = laureate_data[u'laureates'][0]['bornCountryCode']
        except:
            bornCountryCode = ''

        try:
            bio_url = 'http://www.nobelprize.org/nobel_prizes/' + category + '/laureates/' + str(year) + '/' + str(surname).lower() + '-bio.html'
            r = requests.get(bio_url)
            soup=BeautifulSoup(r.text)
            bio_title = soup.find('h1')
            article_body = bio_title.findNextSibling().getText().replace('\r\n',' ').replace('\n',' ')
            bio_title = bio_title.getText()
            if bio_title == 'Page Not Found':
                """ if the page is not found, dont populate the values"""
                bio_title = ''
                article_body = ''
                bio_url = ''
        except Exception,e:
            bio_url = ''
            bio_title = ''
            article_body = ''

        try:
            speech_url = 'http://www.nobelprize.org/nobel_prizes/' + category + '/laureates/'+str(year)+'/'+surname.lower() +'-speech.html'
            rs = requests.get(speech_url)
            if rs.status_code == 404 or 'Read the Banquet Speech' in rs.text:
                """ some nobel speeches end with _en"""
                speech_url = 'http://www.nobelprize.org/nobel_prizes/' + category + '/laureates/'+str(year)+'/'+surname.lower() +'-speech_en.html'
                rs = requests.get(speech_url)
            
            soup=BeautifulSoup(rs.text)
            title = soup.find('h1').getText()            
            try:
                location_date = soup.findAll('p', attrs={'class':'smalltext'})[0].getText()
                date = str(dparser.parse(location_date, fuzzy=True))
            except:
                date = ''
            location = 'Stockholm'            
            
            s = soup.find('h1')
            speech_text = ''
            while True:
                n = s.findNextSibling()
                if n.name in ['p', 'img']:
                    speech_text = speech_text + ' ' + n.getText().replace('\r\n',' ').replace('\n',' ')
                    s = n
                else:
                    break
                
            if title == 'Page Not Found':
                """ if the page is not found, dont populate the values"""
                speech_text = ''
                speech_url = ''
                location = ''
        except Exception,e:
            print str(e)
            speech_url = ''
            location = ''
            date = ''
            speech_text = ''

        try:
            lecture_url = 'http://www.nobelprize.org/nobel_prizes/' + category + '/laureates/' + str(year) +'/'+surname.lower() +'-lecture.pdf'
            lecture_url_html = 'http://www.nobelprize.org/nobel_prizes/' + category + '/laureates/' + str(year) +'/'+surname.lower() +'-lecture.html'
            d = requests.get(lecture_url_html)
            k = requests.get(lecture_url)
            if k.status_code == 404 or 'Page Not Found' in k.text:
                """ some nobel lectures end with _en"""
                lecture_url = 'http://www.nobelprize.org/nobel_prizes/' + category + '/laureates/' + str(year) +'/'+surname.lower() +'-lecture_en.pdf'
                k = requests.get(lecture_url)
                if k.status_code== 200:
                    pdfFileName = download_file(lecture_url)            
                    pdfData = readPDF(pdfFileName)
                else:
                    pdfData = ''
                    lecture_url = ''
            elif k.status_code== 200:
                pdfFileName = download_file(lecture_url)            
                print pdfFileName
                pdfData = readPDF(pdfFileName)            
            
            soup = BeautifulSoup(d.text)
            text = soup.find('div', attrs = {'class':'video_main'}).getText()
            location_lecture = 'Stockholm'
            
            date_lecture = str(dparser.parse(text, fuzzy=True))
            if url == '':
                location_lecture = ''
                date_lecture = ''
        except Exception,e:
            print str(e)
            lecture_url = ''
            text = ''
            date_lecture = ''
            location_lecture = ''
            pdfData = ''

        ## create a dict object with all the values
        json_data = {'first_name':unidecode(firstname), 
                'last_name': unidecode(surname),
                'share':share,
                'id':id,
                'gender':gender,
                'motivation':unidecode(motivation), 
                'affiliations':affiliations,
                'birth_country':bornCountry,
                'bornCountryCode':bornCountryCode,
                'birth_city':bornCity,
                'birth_date':born,
                'death_country':diedCountry,
                'death_city':diedCity,
                'diedCountryCode':diedCountryCode,
                'death_date':died,
                'year':year,
                'area':category,
                'bio':
                    {'words': unidecode(article_body),
                    'url': bio_url,
                     'title': bio_title}
                 ,
                     
                'speech':
                 {'words' : unidecode(speech_text),
                  'date': date,
                  'location': location,
                  'url':speech_url
                  }
                 ,
                'lecture':
                    {'words' :unidecode(pdfData) ,
                    'date': date_lecture,
                    'location': location_lecture,
                    'url': lecture_url}
                 }
        ## write the dict as json
        f = open(firstname + ' ' + surname + '.json', 'wb')
        data_ = json.dumps(json_data)
        f.write((data_))
        f.close()

        print firstname + ' ' + surname + '.json' + '  written'
        
    
