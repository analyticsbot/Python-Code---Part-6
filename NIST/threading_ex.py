import threading, sys
from random import randint
from time import sleep


def print_number(number):
    # Sleeps a random 1 to 10 seconds
    rand_int_var = randint(1, 10)
    sleep(rand_int_var)
    print "Thread " + str(number) + " slept for " + str(rand_int_var) + " seconds"

thread_list = []

for i in range(1, 5):
    # Instantiates the thread
    # (i) does not make a sequence, so (i,)
    t = threading.Thread(target=print_number, args=(i,))
    # Sticks the thread in a list so that it remains accessible
    thread_list.append(t)

# Starts threads
for thread in thread_list:
    thread.start()

while len(thread_list) > 0:
    try:
        # Join all threads using a timeout so it doesn't block
        # Filter out threads which have been joined or are None
        thread_list = [t.join(1000) for t in thread_list if t is not None and t.isAlive()]
    except KeyboardInterrupt:
        sys.exit(1)
        quit()
        print "Ctrl-c received! Sending kill to threads..."
        for t in thread_list:
            t.kill_received = True
# Demonstrates that the main process waited for threads to complete
print "Done"
