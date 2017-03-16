# -*- coding: cp1252 -*-
from bs4 import BeautifulSoup
import requests
import re
import json
import string
import sys
import time
from newspaper import Article
from text_unidecode import unidecode
from threading import Thread
import logging
import os

logging.basicConfig(filename='macfound.log', filemode='a', \
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s'\
                    , datefmt='%H:%M:%S', level=logging.DEBUG)

# debug = True will output what the code is doing, False will not.
debug = True
num_threads = 5
logging.info('Number of threads used = ' + str(num_threads))

# valid chars for file names
valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
logging.info('Valid characters for a file name used = ' + str(valid_chars))
    
if debug:
    print 'All modules loaded. Starting the scraping.', '\n'

def getFellowData(id, valid_chars):
    """Function to pull data on fellows
    id - id of the fellow on macfound.org
    valid_chars - while saving the name/ media json file, convert the filename
    to acceptable value
    df - pandas dataframe that stores the values
    """
    url = 'https://www.macfound.org/fellows/' + str(id) + '/'
    if debug:
        print 'Visiting url - ', url, ' for scraping', '\n'
        logging.info('Visiting url - ' + url + ' for scraping'+ '\n')
    resp = requests.get(url)
    if resp.status_code == 200:
        if debug:
            print 'Success!! Received a 200 response from the server for fellow id', \
                  str(id), '\n'
            logging.info('Success!! Received a 200 response from the server for fellow id'+ \
                  str(id) +'\n')
    else:
        if debug:
            print 'Failure!! Didnt receive 200 response from the server for fellow id',\
                  str(id), '\n'
            logging.error('Failure!! Didnt receive 200 response from the server for fellow id'+\
                  str(id)+'\n')

    if 'Sorry' in unidecode(resp.text):
        if debug:
            print 'No more fellows to scrape. Exiting', '\n'
            logging.info('No more fellows to scrape. Exiting' + '\n')
        sys.exit(1)  # Exit when no more profiles exist

    # Read the content of the response and pass it to beautifulsoup
    # to create a soup object
    soup = BeautifulSoup(unidecode(resp.text))

    # parse the fellow information from the response
    fellow_information = soup.find(attrs={'class': 'fellow-information'})

    # Use fellow_information to extract name, title, publication date
    try:
        fellow_name = fellow_information.find('h1').getText()
        logging.info('Fellow name  == ' + unidecode(fellow_name))
    except:
        fellow_name = ''

    if debug:
        print 'Fellow name is -- ', unidecode(fellow_name)

    try:
        fellow_title = fellow_information.find('h3').getText()
        logging.info('Fellow title  == ' + unidecode(fellow_title))
    except:
        fellow_title = ''
    try:
        pub_date = str(
            fellow_information.find('h6').getText()).replace(
            'Published', '').strip()
    except:
        pub_date = ''
    fellow_designation = ''
    fellow_school = ''
    fellow_location = ''
    fellow_age = ''
    fellow_deceased = ''

    # get the school, designation, age, deceased values wherever present
    try:
        p_tags = fellow_information.findAll('p')
        for tag in p_tags:
            if 'Age' in tag.getText():  # check if the text has Age
                fellow_age = re.findall(r'\d+', tag.getText())[0]
                ix = p_tags.index(tag)
                fellow_location = p_tags[ix - 1].getText()
                if ix - 2 >= 0:
                    fellow_school = p_tags[ix - 2].getText()
                else:
                    fellow_school = ''
                if ix - 3 >= 0:
                    fellow_designation = p_tags[ix - 3].getText()
                else:
                    fellow_designation = ''
            elif 'Deceased' in tag.getText():  # check if the text has Deceased
                fellow_deceased = tag.getText().replace('Deceased:', '')
        logging.info('Scraped age, location, designtion for fellow ' + unidecode(fellow_name))
            
    except:
        logging.error('Not able to scrape age, location, designtion for fellow :: ' + unidecode(fellow_name) + '\n')

    # extract the article body
    try:
        fellow_article_body = unidecode(
            soup.find(
                'div', attrs={
                    'class': 'fellow-profile-bio user-generated clearfix'}).getText())
    except:
        fellow_article_body = ''

    # get the photos of the fellow
    c = 0
    fellow_photos = {}
    try:
        photos = soup.findAll('li', attrs={'class': 'media'})
        logging.info('Number of photos for fellow ' + unidecode(fellow_name) + ' == ' + str(len(photos)))
        for p in photos:
            fellow_photos[
                'photo_' + str(c)] = 'https://www.macfound.org' + p.find('a')['href']
            c += 1
    except:
        pass

    # get any additional information on the fellow
    try:
        fellow_additional_information = soup.find(
            'div', attrs={'class': 'fellow-additional-information'}).find('a')['href']
    except:
        fellow_additional_information = ''

    if debug:
        print 'Successfully scraped data for :: ', unidecode(fellow_name),\
              '. Writing it to json file', '\n', '\n'

    # write the fellow summary to file
    f = open(fellow_name.replace(' ', '_') + '_summary.json', 'wb')

    data = {
        'fellow_name': fellow_name,
        'fellow_title': fellow_title,
        'pub_date': pub_date,
        'fellow_designation': fellow_designation,
        'fellow_school': fellow_school,
        'fellow_location': fellow_location,
        'fellow_age': fellow_age,
        'fellow_deceased': fellow_deceased,
        'fellow_photos': str(fellow_photos),
        'fellow_additional_information': fellow_additional_information,
        'fellow_url': url,
        'fellow_article_body': fellow_article_body}
    f.write(json.dumps(data))
    f.close()

    if debug:
        print 'Successfully written data for', unidecode(fellow_name), ' to file -- ', \
              fellow_name.replace(' ', '_') + '_summary.json', '\n'
        logging.info('Successfully written data for ' +  unidecode(fellow_name) + ' to file -- '+\
              fellow_name.replace(' ', '_') + '_summary.json' + '\n')

    # write the fellow media summary to file
    fellow_articles = soup.findAll(
        attrs={'class': 'promo default in-the-media '})
    article_data = writeFellowMediaData(fellow_articles)
    try:
        title = article_data['title']

        file_name = fellow_name.replace(
            ' ', '_') + '_media_' + title.replace(' ', '_') + '.json'
        file_name = ''.join(c for c in file_name if c in valid_chars)
        f = open(file_name, 'wb')
        f.write(json.dumps(article_data))
        f.close()

        if debug:
            print 'Successfully written media data for', unidecode(fellow_name), \
                  ' to file  -- ', \
                  file_name, '\n', '\n'
            logging.info('Successfully written media data for '  + unidecode(fellow_name)+ \
                  ' to file  -- '+ file_name+ '\n'+ '\n')

    except:
        logging.error('Failure writing media data for '  + unidecode(fellow_name)+ \
                  ' to file  -- '+ file_name+ '\n'+ '\n')


def writeFellowMediaData(fellow_articles):
    """Function to get media data on each fellow
    fellow_articles -- parsed soup on each fellow
    """

    for articles in fellow_articles:
        # grasp the link to the external article on the fellow
        link = articles.find('a', attrs={'class': 'icon'})['href']
        # grasp the title of the link
        title = unidecode(articles.find('h3').getText())

        # download the article using newspaper and parse it
        article = Article(link)
        article.download()
        article.parse()

        # extract authors, publication date, text,
        # images, title, keywords, tags from the data
        article_authors = str(article.authors)
        article_publish_date = str(article.publish_date)
        article_text = unidecode(article.text)
        article_top_image = article.top_image
        article_videos = article.movies
        article_title = article.title
        article_all_images = str(article.images)
        article_keywords = str(article.keywords)
        article_tags = str(list(article.tags))

        # store the values in a dict and return back

        article_data = {
            'article_link': link,
            'title': title,
            'article_authors': article_authors,
            'article_publish_date': article_publish_date,
            'article_text': article_text,
            'article_top_image': article_top_image,
            'article_videos': article_videos,
            'article_title': article_title,
            'article_all_images': article_all_images,
            'article_keywords': article_keywords,
            'article_tags': article_tags}
        return article_data

fellow_id = 1

while True:
    threads = []
    for i in range(num_threads):
        # intialize the threads
        logging.info('Initializing thread ## ' + str(i) +' \n')
        threads.append(
            Thread(
                target=getFellowData,
                args=(
                    fellow_id,
                    valid_chars,
                )))
        fellow_id += 1
    # start the threads
    for t in threads:
        logging.info('Starting thread ## ' + str(i)+ ' \n')
        t.start()
    # wait for the threads to end
    for t in threads:
        logging.info('Closing thread ## ' + str(i) +' \n')
        t.join()
