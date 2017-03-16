## import all modules
from selenium import webdriver
from datetime import timedelta
import argparse
from multiprocessing import Process, Queue
import multiprocessing
import logging, sys
import operator, time, sqlite3
from pyvirtualdisplay import Display
from selenium import webdriver
from apscheduler.schedulers.blocking import BlockingScheduler

try:
    display = Display(visible=0, size=(800, 600))
    display.start()
except:
    pass

sched = BlockingScheduler()

logging.basicConfig(
    filename='namejet.log',
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

## initialize the argument parser
def fetchDomains(c, conn):
    query = 'select domain, price, timeScraped, waitingtime, bid from namejet where bid = 0;'
    c.execute(query)
    domain_price_ = c.fetchall()
    #domain_price_list = "brava.com,6900".split() ## sample
    domain_price_list = ''
    for dp in domain_price_:
        domain = dp[0]
        price = dp[1]
        domain_price_list = domain_price_list + domain + ',' + price + ' '
    return domain_price_list[:-1].split()

## initialize a sqlite db with 4 columns including primary ID
## col1 = domain, col2 = at what time the url was scraped for closing time
## col3 = time the script had to sleep relative to col2 time, col4 = whether a succesfull bid was placed

def login(driver, username, password, login_url, debug):
    time.sleep(2)
    driver.get(login_url)
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

def makeBid(domain, time_sleep, driver, domain_price_dict):
    """Function to bid on a particular domain"""
    url = domain_url.replace('{domain}', domain)
    driver.get(url)
    if time_sleep>0:
        time.sleep(time_sleep)
    try:
        bidBox = driver.find_element_by_name('ctl00$ContentPlaceHolder1$txtBidAmount')
    except:
        try:
            bidBox = driver.find_element_by_name('ctl00_ContentPlaceHolder1_TextBox1')
        except:
            try:
                bidBox = driver.find_element_by_name('ctl00$ContentPlaceHolder1$TextBox1')
            except:
                try:
                    bidBox = driver.find_element_by_class_name('sTxtSm2')
                except:
                    pass
                
    price = domain_price_dict[domain]
    
    try:
        bidBox.send_keys(price)
        driver.find_element_by_name('ctl00$ContentPlaceHolder1$ImageButtonPlaceBid').click()
    except:
        pass

def updateBidURLTime(c, conn, domain, price, time_scrape, time_sleep, bid):
    update_url_query = 'UPDATE namejet SET timeScraped = ' + '"' + str(time_scrape) + \
                       '", price = "' + str(price) + '", waitingtime =' + str(time_sleep) + \
                       ', bid = 0 WHERE domain = "' + str(domain)+ '";'
    c.execute(update_url_query)
    conn.commit()

def updateBidDomains(c, conn, domain):
    update_url_query = 'UPDATE namejet SET bid = 1 WHERE domain = "' + str(domain)+ '";'
    c.execute(update_url_query)
    conn.commit()

def main(c, conn, driver, debug):
    print('Checking the updated list of domains.')    
    logging.info('Opened the login url')
    login(driver, username, password, login_url, debug)
    domain_price_list = fetchDomains(c, conn)
    print 'domain_price_list', domain_price_list
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
        url = domain_url.replace('{domain}', domain)
        query = 'SELECT domain, price, timeScraped, waitingtime, bid FROM namejet WHERE domain="' + domain +'"'
        c.execute(query)
        rows = c.fetchone()
        price, timeScraped, waitingtime, bid = rows[1], rows[2], rows[3], int(rows[4])
        ## check whether a bid has been succesfully placed. If yes, move to next domain. Nothing to do here

        time_now = time.time()
        time_elapsed = time_now - float(timeScraped)
        time_left_seconds = waitingtime - time_elapsed
        updateBidURLTime(c, conn, domain, price, time_now, time_left_seconds, bid)
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
            makeBid(domain, 0, driver, domain_price_dict)
            updateBidDomains(c, conn, domain)
            logging.info('Bid placed on :: ' + url)
            if debug:
                ('Bid placed on :: ' + url)
        else:
            time_left_seconds = time_left_seconds-300
            if time_left_seconds<0:
                print 'bidding for domain name :: ', domain
                logging.info('bidding for domain name :: ' + domain)
                makeBid(domain, 0, driver, domain_price_dict)
                updateBidDomains(c, conn, domain)
                logging.info('Bid placed on :: ' + url)
                if debug:
                    ('Bid placed on :: ' + url)
            else:
                domain_time[domain] = time_left_seconds

    ## now that the script has calculated how time it should sleep
    ## for each domain, reduce the time taken to perform the above
    ## calculated
    done = time.time()
    for key, value in elapsed_time.iteritems():
        time_taken = done - elapsed_time[key]
        try:
            domain_time[key] = domain_time[key] - time_taken
        except:
            pass

    ## sort the domain and the wait time in ascending order
    ## for each successive bid, wait some amount of time
    ## this time would be time for this domain - time already waited for the previous
    ## domain
    sorted_domain_time = sorted(domain_time.items(), key=operator.itemgetter(1))
    lag_time = 0.0
    for value in sorted_domain_time:
        domain, time_sleep = value[0], value[1]
        time_sleep_new =  float(time_sleep)-lag_time
        print 'bidding for domain name :: ', domain
        logging.info('Sleeping for :: ' + str(time_sleep_new) + ' for domain ::' + domain)
        if debug:
            print ('Sleeping for :: ' + str(time_sleep_new) + ' for domain ::' + domain)
            
        url = domain_url.replace('{domain}', domain)
        
        logging.info('bidding for domain name :: ' + domain)
        makeBid(url, time_sleep_new, driver, domain_price_dict)
        updateBidDomains(c, conn, domain)
        logging.info('Bid placed on :: ' + url)
        if debug:
            print ('Bid placed on :: ' + url)
        lag_time = time_sleep

    if debug:
        print 'All voting done'
       
if __name__ == '__main__':
    @sched.scheduled_job('interval', hours = 1)
    def timed_job():
        conn = sqlite3.connect('namejetDB2.db')
        c = conn.cursor()
        check_table_query = 'select name from sqlite_sequence where name = "namejet" ;'
        c.execute(check_table_query)
        rows = c.fetchone()
        if rows is None:
            if debug:
                print 'Table namejet does not exists. Exiting'
                logging.info('Table namejet does not exists. Exiting')
                sys.exit(1)

        logging.info('Using username = ' + username + ' ; & password = ' + password + ' to login')
        driver = webdriver.Firefox()
        main(c, conn, driver, debug)
        driver.close()
        c.close()
        conn.close()

    sched.start()    
    


        
