from bs4 import BeautifulSoup
from BeautifulSoup import BeautifulSoup
from textblob import TextBlob
import pandas as pd
import dateutil.parser as dparser

df = pd.DataFrame(columns = ['Email_Body', 'polarity', 'subjectivity', 'num_words_doc', 'email_title', 'date_time', 'document_idx', 'newpaper_title'])
## this is the input html file.  Need to change that
f = open('Nike1991.HTML', 'r')
data = f.read()
soup = BeautifulSoup(data)
emails = soup.findAll('div')

body = ''
sentiment_polarity  = ''
sentiment_subjectivity = ''
num_words_doc = ''
email_title = ''
date_time = ''
document_idx = ''

for i in soup.findAll('div'):
    if (BeautifulSoup(str(i)).findAll(attrs = {'class':'c5'})):
        if (BeautifulSoup(str(i)).findAll(attrs = {'class':'c4'}) and BeautifulSoup(str(i)).findAll(attrs = {'class':'c2'})):
            body = body + i.getText()
            
    elif (BeautifulSoup(str(i)).findAll('table', attrs = {'class':'c12'})):
        body+=i.getText()

    if 'LENGTH:' in i.getText():
        num_words_doc = i.getText().replace('LENGTH:','').strip()

    if (BeautifulSoup(str(i)).findAll(attrs = {'class':'c7'})) or (BeautifulSoup(str(i)).findAll(attrs = {'class':'c8'})):
        email_title = i.getText().strip()

    if (BeautifulSoup(str(i)).findAll(attrs = {'class':'c1'})):
        if (BeautifulSoup(str(i)).findAll(attrs = {'class':'c4'})): # and BeautifulSoup(str(i)).findAll(attrs = {'class':'c2'})):
            try:
                date_time = dparser.parse(i.getText(),fuzzy=True)
            except:
                date_time = ''

    if ('DOCUMENT' in i.getText()) and ('of' in i.getText()):
        document_idx = i.getText()
        newpaper_title = i.findNextSibling('div').getText()
            
    if (BeautifulSoup(str(i)).findAll(attrs = {'class':'c11'})):
        nr = df.shape[0]-1
        blob = TextBlob(body)
        sentiment_polarity = blob.sentiment.polarity
        sentiment_subjectivity = blob.sentiment.subjectivity
        #df.loc[nr+1] = [body]
        df.loc[nr+1] = [body, sentiment_polarity, sentiment_subjectivity, num_words_doc, email_title, date_time, document_idx, newpaper_title]
        body = ''
        sentiment_polarity  = ''
        sentiment_subjectivity = ''
        num_words_doc = ''
        email_title = ''
        date_time = ''
        document_idx = ''
        newpaper_title = ''
                             
                
nr = df.shape[0]-1
blob = TextBlob(body)
sentiment_polarity = blob.sentiment.polarity
sentiment_subjectivity = blob.sentiment.subjectivity
df.loc[nr+1] = [body, sentiment_polarity, sentiment_subjectivity, num_words_doc, email_title, date_time, document_idx, newpaper_title]

df.to_csv('parsed_data_1991_vf1.csv', index = False, encoding = 'utf-8')
