from bs4 import BeautifulSoup
from BeautifulSoup import BeautifulSoup
from textblob import TextBlob
import pandas as pd
import dateutil.parser as dparser

df = pd.DataFrame(columns = ['Email_Body', 'polarity', 'subjectivity', 'num_words_doc', 'email_title'])
## this is the input html file.  Need to change that
f = open('Nike1991.HTML', 'r')
data = f.read()
soup = BeautifulSoup(data)
emails = soup.findAll(attrs = {'class':'c5'})

counter = 0
for email in emails:
    try:
        text = email.getText().lower().strip()
        if 'length' in text:
            num_words = text.replace('length:','').strip()
        soup1 = BeautifulSoup(str(email))
        if (soup1.findAll(attrs = {'class':'c7'})):# and soup1.findAll(attrs = {'class':'c8'})):
            title = email.getText().strip()
            
        if ((len(soup1.findAll(attrs = {'class':'c4'})) >=2) and (len(soup1.findAll(attrs = {'class':'c2'})) >=2)):
            body = email.getText()
            blob = TextBlob(body)
            sentiment_polarity = blob.sentiment.polarity
            sentiment_subjectivity = blob.sentiment.subjectivity
            num_words_doc = num_words
            email_title = title
            df.loc[counter+1] = [body, sentiment_polarity, sentiment_subjectivity, num_words_doc, email_title]
            counter +=1
    except:
        pass
    
print counter
date_column = []
dates = soup.findAll(attrs = {'class':'c3'})
for d in dates:
    soup2 = BeautifulSoup(str(d))
    if (soup2.findAll(attrs = {'class':'c4'}) and soup2.findAll(attrs = {'class':'c2'})):
        date = d.getText().strip()
        try:
            date = str(dparser.parse(date,fuzzy=True))
            date_column.append(date)
        except:
            date_column.append(date)
print len(dates)
document_idx = []
docs = soup.findAll(attrs = {'class':'c0'})
for d in docs:
    text = d.getText().strip()
    if 'DOCUMENT' in text:
        document_idx.append(text)
print len(document_idx)
## this is the outputfile name ==  parsed_data1.csv. You can change that
## to whatever you want.
df['date'] = (date_column)
df['docIndex'] = (document_idx)
df.to_csv('parsed_data4.csv', index = False, encoding = 'utf-8')
