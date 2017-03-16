## import all modules
from selenium import webdriver
from datetime import timedelta
import argparse
from multiprocessing import Process, Queue
import multiprocessing
import logging
import operator, time, sqlite3
from pyvirtualdisplay import Display

try:
    display = Display(visible=0, size=(800, 600))
    display.start()
except:
    pass

logging.basicConfig(
    filename='namejet_add_domains.log',
    filemode='a',
    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
    level=logging.DEBUG)

logging.info('All required modules have been imported')

## static variables
username = 'c3542803' ## username for login
password = 'facebook123' ## password for login
login_url = 'https://www.namejet.com/Pages/Login.aspx?'
domain_url = 'http://www.namejet.com/Pages/Auctions/BackorderDetails.aspx?domainname={domain}'
debug = True

logging.info('Using username = ' + username + ' ; & password = ' + password + ' to login')

## initialize the argument parser
parser = argparse.ArgumentParser()
parser.add_argument('-dp', help='"domain1,price1 domain2,price2 domain3,price3"')
args = parser.parse_args()
domain_price_list = args.dp.strip().split()
#domain_price_list = "brava.com,6900".split() ## sample

driver = webdriver.Firefox()
driver.get(login_url)
logging.info('Opened the login url')

## initialize a sqlite db with 4 columns including primary ID
## col1 = domain, col2 = at what time the url was scraped for closing time
## col3 = time the script had to sleep relative to col2 time, col4 = whether a succesfull bid was placed
conn = sqlite3.connect('namejetDB2.db')
c = conn.cursor()
create_table_query = 'CREATE TABLE  namejet ( ID INTEGER PRIMARY KEY AUTOINCREMENT, domain CHAR(5000), price TEXT, timeScraped TEXT, waitingTime  INT, bid INT);'
try:
    c.execute(create_table_query)
    conn.commit()
    if debug:
        print 'Table namejet does not exists. Created'
        logging.info('Table namejet does not exists. Created')
except:
    if debug:
        print 'Table namejet already exists.'
        logging.info('Table namejet already exists.')

time.sleep(2)        
username_field = driver.find_element_by_name('ctl00$ContentPlaceHolder1$txtUsername')
username_field.send_keys(username)
password_field = driver.find_element_by_name('ctl00$ContentPlaceHolder1$txtPassword')
password_field.send_keys(password)
driver.find_element_by_name('ctl00$ContentPlaceHolder1$btnSubmit').click()
logging.info('Successfully logged in')
if debug:
    print 'Successfully log in!!'

UNITS = {"s":"seconds", "m":"minutes", "h":"hours", "d":"days", "w":"weeks"}

def convert_to_seconds(s):
    """Function to convert namejet time to seconds"""
    count = int(s[:-1])
    unit = UNITS[ s[-1] ]
    td = timedelta(**{unit: count})
    return td.seconds + 60 * 60 * 24 * td.days

def makeBid(domain, time_sleep):
    """Function to bid on a particular domain"""
    url = domain_url.replace('{domain}', domain)
    driver.get(url)
    time.sleep(time_sleep)
    try:
        bidBox = driver.find_element_by_name('ctl00$ContentPlaceHolder1$txtBidAmount')
    except:
        bidBox = driver.find_element_by_name('ctl00_ContentPlaceHolder1_TextBox1')
    
    price = domain_price_dict[domain]
    
    try:
        bidBox.send_keys(price)
        driver.find_element_by_name('ctl00$ContentPlaceHolder1$ImageButtonPlaceBid').click()
    except:
        pass

def insertBidURLTime(domain, price, time_scrape, time_sleep, bid):
    insert_url_query = 'INSERT INTO namejet (domain, price, timeScraped, waitingtime, bid)  VALUES ("' + str(domain) +'",' + \
                       '"'+str(price) + '",' + '"'+str(time_scrape) + '",' + str(time_sleep) + ', ' + str(0) + ');'
    c.execute(insert_url_query)
    conn.commit()

def updateBidURLTime(domain, price, time_scrape, time_sleep, bid):
    update_url_query = 'UPDATE namejet SET timeScraped = ' + '"' + str(time_scrape) + '", price = "' + str(price) + '" waitingtime =' + str(time_sleep) + \
                       ', bid = 0 WHERE domain = "' + str(domain)+ '";'
    c.execute(update_url_query)
    conn.commit()

def updateBidDomains(domain):
    update_url_query = 'UPDATE namejet SET bid = 1 WHERE domain = "' + str(domain)+ '";'
    c.execute(update_url_query)
    conn.commit()

## iterate through the arguments provided and store domain price as key value pair
domain_price_dict = {}
for domain_price in domain_price_list:
    domain, price = domain_price.split(',')[0], domain_price.split(',')[1]
    domain_price_dict[domain] = price

logging.info('Dictionary of domain bid price :: ' + str(domain_price_dict))

## iterate through all the domains and store how much time the wait should be
## ideally the bot should vote 5 mins before. Iterating and finding the time to sleep
## this would take some time. This time should be deducted from original time
## domain_time stores the time mentioned on namejet.com for a domain
## elapsed_time stores how much time passed after time was scraped from namejet
## for a domain till all times are scraped
domain_time = {}
elapsed_time = {}
for domain_price in domain_price_list:
    domain, price = domain_price.split(',')[0], domain_price.split(',')[1]

    ## check if an entry exists in the db for this domain
    query = 'SELECT domain, price, timeScraped, waitingtime, bid FROM namejet WHERE domain="' + domain +'"'
    c.execute(query)
    rows = c.fetchone()
    url = domain_url.replace('{domain}', domain)
    if rows is None:
        
        logging.info('Visiting url :: ' + url + ' for getting time')
        if debug:
            print ('Visiting url :: ' + url + ' for getting time')
        driver.get(url)
        time_left_seconds = 0

        ## two possible elements where time left is given
        try:
            time_left = driver.find_element_by_id('ctl00_ContentPlaceHolder1_lblTimeLeft').text.strip().split()
        except:
            try:
                time_left = driver.find_element_by_id('ctl00_ContentPlaceHolder1_LabelTimeLeft').text.strip().split()
            except:
                time_left = ['0s']
        ## for the time left, find the time in seconds
        for t in time_left:
            time_left_seconds += convert_to_seconds(t)
        time_scrape = str(time.time())
        logging.info('url :: ' + url + ' has waiting time :: '+  str(time_left_seconds) + ' seconds')
        if debug:
            print ('url :: ' + url + ' has waiting time :: '+  str(time_left_seconds) + ' seconds')

        ## inser this entry into the db
        insertBidURLTime(domain, price, time_scrape, time_left_seconds, 0)
        if debug:
            logging.info('Domain :: ' + str(domain) + ' entry does not exist. Adding one')
            print 'Domain :: ' + str(domain) + ' entry does not exist. Adding one'
        
    else:
        price, timeScraped, waitingtime, bid = rows[1], rows[2], rows[3], str(row[4])
        ## check whether a bid has been succesfully placed. If yes, move to next domain. Nothing to do here
        if bid ==1:
            continue
        time_now = time.time()
        time_elapsed = time_now - float(timeScraped)
        time_left_seconds = waitingtime - time_elapsed
        updateBidURLTime(domain, price, time_now, time_left_seconds, bid)
        if debug:
            logging.info('Domain :: ' + str(domain) + ' entry does exist. Updating...')
            print 'Domain :: ' + str(domain) + ' entry does exist. Updating...'        
    
    ## store this time to calculate how much time elapsed
    elapsed_time[domain] = time.time()

    ## if time left is less than 30 seconds, bid right now
    ## else reduce 5 min (300 seconds) from the bid time
    ## if that time is negative, this means bid now
    ## else store that time in a dictionary domain_time
    if time_left_seconds<30:
        print 'bidding for domain name :: ', domain
        logging.info('bidding for domain name :: ' + domain)
        makeBid(domain, 0)
        updateBidDomains(url)
        logging.info('Bid placed on :: ' + url)
        if debug:
            ('Bid placed on :: ' + url)
    else:
        time_left_seconds = time_left_seconds-300
        if time_left_seconds<0:
            print 'bidding for domain name :: ', domain
            logging.info('bidding for domain name :: ' + domain)
            makeBid(domain, 0)
            updateBidDomains(url)
            logging.info('Bid placed on :: ' + url)
            if debug:
                ('Bid placed on :: ' + url)
        else:
            domain_time[domain] = time_left_seconds

if debug:
    print 'All voting done'
driver.close()
c.close()
conn.close()

    


        
