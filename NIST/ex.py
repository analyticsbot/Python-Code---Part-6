import threading
import time

def timed_output(name, delay, run_event):
    if not run_event.is_set():
        sys.exit(1)
    time.sleep(delay)
    print name,": New Message!"

def timed_output1(name, delay, run_event):
    if not run_event.is_set():
        sys.exit(1)
    time.sleep(delay)
    print name,": Newwwwww Message!"
    
if __name__ == "__main__":
    run_event = threading.Event()
    run_event.set()
    d1 = 1
    threads = []
    for i in range(5):
        threads.append(threading.Thread(target = timed_output, args = ("bob",d1,run_event)))

    d2 = 2
    threads1 = []
    for j in range(5):
        threads1.append(threading.Thread(target = timed_output1, args = ("paul",d2,run_event)))

    for t1 in threads:
        t1.start()
    time.sleep(.5)
    for t2 in threads1:
        t2.start()

    try:
        while 1:
            time.sleep(.1)
    except KeyboardInterrupt:
        print "attempting to close threads. Max wait =",max(d1,d2)
        run_event.clear()
        t1.join()
        t2.join()
        print "threads successfully closed"
