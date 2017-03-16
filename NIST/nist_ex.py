            # import all necessary modules
            import Queue
            import logging
            import multiprocessing
            import time, sys
            import signal

            debug = True

            def init_worker():
                signal.signal(signal.SIGINT, signal.SIG_IGN)

            research_name_id = {}
            ids = [55, 125, 428, 429, 430, 895, 572, 126, 833, 502, 404]
            # declare all the static variables
            num_threads = 2  # number of parallel threads

            minDelay = 3  # minimum delay between get requests to www.nist.gov
            maxDelay = 7  # maximum delay between get requests to www.nist.gov

            # declare an empty queue which will hold the publication ids
            queue = Queue.Queue(0)


            proxies = []
            #print (proxies)

            def split(a, n):
                """Function to split data evenly among threads"""
                k, m = len(a) / n, len(a) % n
                return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)]
                        for i in xrange(n))
            def run_worker(
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
                print 'getLinks', i
                for d in data:
                    print d
                    queue.put(d)
                



            def fun_worker(i, queue, proxies, debug, minDelay, maxDelay):
                print 'publicationData', i
                try:
                    print queue.pop()
                except:
                    pass
                



            def main():
                print "Initializing workers"
                pool = multiprocessing.Pool(num_threads, init_worker)
                distributed_ids = list(split(list(ids), num_threads))
                for i in range(num_threads):
                    data_thread = distributed_ids[i]
                    print data_thread
                    pool.apply_async(run_worker, args=(i + 1,
                            data_thread,
                            queue,
                            research_name_id,
                            proxies,
                            debug,
                            minDelay,
                            maxDelay,
                        ))
                    
                    pool.apply_async(fun_worker,
                        args=(
                            i + 1,
                            queue,
                            proxies,
                            debug,
                            minDelay,
                            maxDelay,
                        ))

                try:
                    print "Waiting 10 seconds"
                    time.sleep(10)

                except KeyboardInterrupt:
                    print "Caught KeyboardInterrupt, terminating workers"
                    pool.terminate()
                    pool.join()

                else:
                    print "Quitting normally"
                    pool.close()
                    pool.join()

            if __name__ == "__main__":
                main()

                

