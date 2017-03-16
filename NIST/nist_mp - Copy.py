# import all necessary modules
import mechanize
import json
import urllib2
import os
import sys
import string
import time
import random
import requests
import re
from bs4 import BeautifulSoup
import pandas as pd
from multiprocessing import Process, Queue
from text_unidecode import unidecode
from pyPdf import PdfFileReader
import logging
import multiprocessing
import math
import os
import boto
from filechunkio import FileChunkIO
from boto.s3.connection import S3Connection
import subprocess

logging.basicConfig(
    filename='nist.log',
    filemode='a',
    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
    level=logging.DEBUG)

AWS_Access_Key = ''
AWS_Secret_Access_Key = ''
S3_BUCKET_NAME = ''

# Connect to S3
c = S3Connection(AWS_Access_Key, AWS_Secret_Access_Key)
b = c.get_bucket(S3_BUCKET_NAME)

# if debug is set as True, updates will be printed on sysout
debug = True

if not os.path.exists('success'):
    os.makedirs('success')

if not os.path.exists('failures'):
    os.makedirs('failures')

# read the id name file made after running get_research_id_name.py
# and add to a dictionary which will be used to the name of
# the research field the script is currently working on
# itertate through all the rows of the dataframe
research_name_id = {}
df = pd.read_csv('research_name_ids.csv')
ids = df['research_id']
for i, row in df.iterrows():
    research_name_id[row[0]] = row[1]

logging.info('Read the put file for research id and name')

# declare all the static variables
num_threads = 2  # number of parallel threads
valid_chars = "-_.() %s%s" % (string.ascii_letters,
                              string.digits)  # valid chars for file names

logging.info('Number of threads ' + str(num_threads))

minDelay = 3  # minimum delay between get requests to www.nist.gov
maxDelay = 7  # maximum delay between get requests to www.nist.gov

logging.info('Minimum delay between each request =  ' + str(minDelay))
logging.info('Maximum delay between each request =  ' + str(maxDelay))

# search_base_urls have the same pattern
# just need to change the research field and page on the first and
search_base_url = 'http://www.nist.gov/publication-portal.cfm?researchField={researchField}&sortBy=date&page={page}'


def getProxies():
    """function to get the list of proxies
    To avoid getting blocked or any 403 errors, using proxies from free proxy
    list
    """
    proxy = []
    url = 'https://free-proxy-list.net/'
    response = requests.get(url)
    html = response.content

    templs = re.findall(r'<tr><td>(.*?)</td><td>', html)
    templs2 = re.findall(r'</td><td>[1-99999].*?</td><td>', html)

    for i in range(len(templs)):
        ip = (templs[i] + ":" + templs2[i].replace('</td><td>', ''))
        proxy_ip = 'http://' + ip

        # check if the proxy is working, else dont use it.
        # by putting a get request to api.ipify.org with a http proxy, it
        # returns the same proxy
        # back, which means the proxy is working
        if requests.get('https://api.ipify.org',
                        proxies={'http': proxy_ip}).content == ip:
            proxy.append(proxy_ip)

    if debug:
        sys.stdout.write(('Total proxies downloaded' + str(len(proxy) + '\n')))
        logging.info(('Total proxies downloaded' + str(len(proxy) + '\n')))
    return proxy

# call the getProxies function
#proxies = getProxies()
proxies = []


def uploadDataS3(source_path, b):
    # Get file info
    source_size = os.stat(source_path).st_size

    # Create a multipart upload request
    mp = b.initiate_multipart_upload(os.path.basename(source_path))

    # Use a chunk size of 50 MiB (feel free to change this)
    chunk_size = 52428800
    chunk_count = int(math.ceil(source_size / float(chunk_size)))

    # Send the file parts, using FileChunkIO to create a file-like object
    # that points to a certain byte range within the original file. We
    # set bytes to never exceed the original file size.
    for i in range(chunk_count):
        offset = chunk_size * i
        bytes = min(chunk_size, source_size - offset)
        with FileChunkIO(source_path, 'r', offset=offset,
                         bytes=bytes) as fp:
            mp.upload_part_from_file(fp, part_num=i + 1)

    # Finish the upload
    mp.complete_upload()


def readPDF(filename):
    """Function to read the attachment and return the contents"""
    subprocess.call(['pdftotext',filename, filename[:-4] + '.txt'])
    f = open(filename[:-4] + '.txt', 'rb')
    content = f.read()
    return content


def download_file(url, name):
    """ function to download the files to local"""
    local_filename = name + '.pdf'
    r = requests.get(url, stream=True)
    with open(local_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
    return local_filename


def split(a, n):
    """Function to split data evenly among threads"""
    k, m = len(a) / n, len(a) % n
    return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)]
            for i in xrange(n))


def getLinks(
        i,
        data,
        queue,
        research_name_id,
        proxies,
        debug,
        minDelay,
        maxDelay):
    """ Function to pull out all publication links from nist
    data - research ids pulled using a different script
    queue  -  add the publication urls to the list
    research_name_id - dictionary with research id as key and name as value
    proxies - scraped proxies
    """
    for d in data:

        # pg_idx is the page index for the research search results.
        # break the while loop if there are no more search results
        # add the links to a local list, and the length to another list
        pg_idx = 1
        local_queue = []
        len_local_queue = [1111, 222, 333, 4444]

        while True:
            url = search_base_url.replace(
                '{researchField}', str(d)).replace(
                '{page}', str(pg_idx))
            if debug:
                sys.stdout.write('Visting url :: ' + url + '\n')

            logging.info('Visting url :: ' + url + '\n')
            pg_idx += 1
            len_local_queue.append(len(local_queue))

            # if the last 2 elements of the local queue are same it means
            # no new data is being added. Exit the loop
            if len_local_queue[-2] == len_local_queue[-1]:
                break

            # intatiate mechanize browser, read the response and pass it to
            # soup
            br = mechanize.Browser()
            logging.info(
                'Intantiated a browser for thread :: ' +
                str(i) +
                '\n')

            if len(proxies) > 5:
                http_proxy = proxies[random.randint(0, len(proxies) - 1)]

                # add proxy
                br.set_proxies({"http": http_proxy})
            header = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 5.1; rv:14.0) Gecko/20100101 Firefox/14.0.1',
                'Referer': 'http://www.nist.com'}

            # wrap the request.
            request = urllib2.Request(url, None, header)

            br.open(request)

            html = br.response().read()
            soup = BeautifulSoup(html, 'lxml')

            a = soup.findAll('a')

            for i in a:
                try:
                    if 'pub_id' in i.getText():
                        queue.put(i.getText())
                        logging.info(
                            'Added publication to queue :: ' + str(i.getText()) + '\n')
                        if i.getText() not in local_queue:
                            local_queue.append(i.getText())
                except:
                    pass
            wait_time = random.randint(minDelay, maxDelay)
            if debug:
                sys.stdout.write('Sleeping for :: ' + str(wait_time) + '\n')

            logging.info('Sleeping for :: ' + str(wait_time) + '\n')
            time.sleep(wait_time)


def getElement(elements, name):
    """Function to extract data from publication page which has data in tables"""
    try:
        for e in elements:
            if unidecode(e.find('th').getText()).strip(
            ) == unidecode(name).strip():
                if name.strip() == 'DOI:':
                    # if DOI is to be extracted, we need the pdf link
                    return e.find('td').find('a')['href']
                else:
                    # for all other elements, text is required
                    return e.find('td').getText().strip()
    except:
        pass


def publicationData(i, queue, proxies, debug, minDelay, maxDelay, b):
    while True:

        try:
            url = queue.get()
        except:
            time.sleep(.1)
            continue
        if url is None:
            break
            sys.exit(1)

        if debug:
            sys.stdout.write('Visting publication url :: ' + url + '\n' + '\n')

        logging.info('Visting publication url :: ' + url + '\n' + '\n')
        br = mechanize.Browser()
        if len(proxies) > 5:
            http_proxy = proxies[random.randint(0, len(proxies) - 1)]

            # add proxy
            br.set_proxies({"http": http_proxy})
        header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 5.1; rv:14.0) Gecko/20100101 Firefox/14.0.1',
            'Referer': 'http://www.nist.com'}

        # wrap the request.
        request = urllib2.Request(url, None, header)
        br.open(request)
        html = br.response().read()
        soup = BeautifulSoup(html, 'lxml')

        try:
            pubDisplay = soup.find('table', attrs={'class': 'pubDisplay'})
        except:
            pass
        try:
            elements = pubDisplay.findAll('tr')
        except:
            elements = ''
        try:
            authors = unidecode(getElement(elements, 'Author(s):'))
        except:
            authors = ''
        try:
            title = unidecode(getElement(elements, 'Title:'))
        except:
            title = ' '
        try:
            published = getElement(elements, 'Published:')
            published = ' '.join(published.split())
        except:
            published = ''
        try:
            abstract = unidecode(getElement(elements, 'Abstract:'))
        except:
            abstract = ''
        try:
            citation = unidecode(getElement(elements, 'Citation:'))
        except:
            citation = ''
        try:
            keywords = unidecode(getElement(elements, 'Keywords:'))
        except:
            keywords = ''
        try:
            volume = unidecode(getElement(elements, 'Volume:'))
        except:
            volume = ''
        try:
            issue = unidecode(getElement(elements, 'Issue:'))
        except:
            issue = ''
        try:
            pages = unidecode(getElement(elements, 'Pages:'))
        except:
            pages = ''
        try:
            dates = unidecode(getElement(elements, 'Dates:'))
        except:
            dates = ''
        try:
            proceedings = unidecode(getElement(elements, 'Proceedings:'))
        except:
            proceedings = ''
        try:
            location = unidecode(getElement(elements, 'Location:'))
        except:
            location = ''
        try:
            research_areas = unidecode(getElement(elements, 'Research Areas:'))
        except:
            research_areas = ''
        try:
            pub_id_ = re.findall(r'\d+', url)[0]

            try:
                doi = getElement(elements, 'DOI:')
                pdf_filename = download_file(doi, pub_id_)
                pdf_text = unidecode(readPDF(pdf_filename).replace('\n', ' '))
            except Exception as e:
                doi = 'http://www.nist.gov/customcf/get_pdf.cfm?pub_id=' + \
                    str(pub_id_)
                pdf_filename = download_file(doi, pub_id_)
                pdf_text = unidecode(readPDF(pdf_filename).replace('\n', ' '))
            pdf_text = ' '.join(pdf_text.split())
            logging.info(
                'Successfully got the pdf for publication id:: ' +
                str(pub_id_))

        except:
            pdf_text = ''
            pdf_filename = ''
            logging.error(
                'Failure in getting the pdf for publication id:: ' +
                str(pub_id_))

        # write the fellow summary to file
        file_name = title.replace(' ', '_') + '.json'
        file_name = ''.join(c for c in file_name if c in valid_chars)
        if pdf_filename != '' and (
            getElement(
                elements,
                'DOI:') or getElement(
                elements,
                'PDF version:')):
            
            if os.name == 'nt':
                f = open('success//' + file_name , 'wb')
            else:
                f = open('success/' + file_name , 'wb')
            folder = 'success'
            logging.info(
                'Opened ' +
                'success//' +
                file_name +
                '.json' +
                ' for writing')
        else:
            if os.name == 'nt':
                f = open('failures//' + file_name , 'wb')
            else:
                f = open('failures/' + file_name , 'wb')
            
            folder = 'failures'
            logging.info(
                'Opened ' +
                'failures//' +
                file_name +
                '.json' +
                ' for writing')

        data = {
            'dates': dates,
            'location': location,
            'proceedings': proceedings,
            'volume': volume,
            'issue': issue,
            'pages': pages,
            'url': url,
            'title': title,
            'authors': authors,
            'published': published,
            'abstract': abstract,
            'citation': citation,
            'keywords': keywords,
            'pdf_filename': pdf_filename,
            'pdf_text': pdf_text}

        f.write(json.dumps(data))
        f.close()
        logging.info('File written ' + file_name)
        if os.name == 'nt':
            uploadDataS3(folder + '//' + file_name, b)
        else:
            uploadDataS3(folder + '/' + file_name, b)

        if debug:
            sys.stdout.write(file_name + ' written' + '\n')
        wait_time = random.randint(minDelay, maxDelay)
        sys.stdout.write('Sleeping for :: ' + str(wait_time) + '\n')
        logging.info('Sleeping for :: ' + str(wait_time) + '\n')
        sys.stdout.write(
            '******************************************' + '\n')
        sys.stdout.write(
            '******************************************' + '\n')
        time.sleep(wait_time)

distributed_ids = list(split(list(ids), num_threads))
if __name__ == "__main__":
    # declare an empty queue which will hold the publication ids
    manager = multiprocessing.Manager()
    queue = manager.Queue()

    logging.info('Initialized an empty queue')

    threads = []
    for i in range(num_threads):
        data_thread = distributed_ids[i]
        threads.append(
            Process(
                target=getLinks,
                args=(
                    i + 1,
                    data_thread,
                    queue,
                    research_name_id,
                    proxies,
                    debug,
                    minDelay,
                    maxDelay,

                )))

    dataThreads = []
    for i in range(num_threads):
        dataThreads.append(
            Process(
                target=publicationData,
                args=(
                    i + 1,
                    queue,
                    proxies,
                    debug,
                    minDelay,
                    maxDelay,
                    b,

                )))

    j = 1
    for thread1 in threads:
        sys.stdout.write('starting link scraper ##' + str(j) + '\n')
        logging.info('starting link scraper ##' + str(j) + '\n')
        j += 1
        thread1.start()

    time.sleep(5)
    j = 1
    for thread in dataThreads:
        sys.stdout.write('starting publication scraper ##' + str(j) + '\n')
        logging.info('starting publication scraper ##' + str(j) + '\n')
        j += 1
        thread.start()

    try:
        for worker in threads:
            worker.join(10)

    except KeyboardInterrupt:
        print 'Received ctrl-c'
        for worker in threads:
            worker.terminate()
            worker.join(10)
    queue.put(None)
    try:
        for worker in dataThreads:
            worker.join(10)
    except KeyboardInterrupt:
        print 'Received ctrl-c'
        for worker in dataThreads:
            worker.terminate()
            worker.join(10)
