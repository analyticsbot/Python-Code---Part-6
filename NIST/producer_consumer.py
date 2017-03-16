import time
import threading
import random

from Queue import Queue, Empty

"""A multi-producer, multi-consumer queue."""

# A thread that produces data
class Producer(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        threading.Thread.__init__(self, group=group, target=target, name=name,
                                  verbose=verbose)
        self.running = True
        self.name = name
        self.args = args
        self.kwargs = kwargs

    def run(self):
        out_q = self.kwargs.get('queue')
        while self.running:
            # Adding some integer
            out_q.put(random.randint(1,1000))
            # Kepping this thread in sleep not to do many iterations
            #time.sleep(0.1)

        print 'producer {name} terminated\n'.format(name=self.name)


# A thread that consumes data
class Consumer(threading.Thread):

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        threading.Thread.__init__(self, group=group, target=target, name=name,
                                  verbose=verbose)
        self.args = args
        self.kwargs = kwargs
        self.producer_alive = True
        self.name = name

    def run(self):
        in_q = self.kwargs.get('queue')

        # Consumer should die one queue is producer si dead and queue is empty.
        while self.producer_alive or not in_q.empty():
            try:
                data = in_q.get(timeout=1)
                print data, '****'
            except Empty, e:
                pass

            # This part you can do anything to consume time
            if isinstance(data, int):
                # just doing some work, infact you can make this one sleep
                print (data)
            else:
                pass
        print 'Consumer {name} terminated (Is producer alive={pstatus}, Is Queue empty={qstatus})!\n'.format(
            name=self.name, pstatus=self.producer_alive, qstatus=in_q.empty())


# Create the shared queue and launch both thread pools
q = Queue()

producer_pool, consumer_pool = [], []


for i in range(1, 3):
    producer_worker = Producer(kwargs={'queue': q}, name=str(i))
    producer_pool.append(producer_worker)
    producer_worker.start()

for i in xrange(1, 5):
    consumer_worker = Consumer(kwargs={'queue': q}, name=str(i))
    consumer_pool.append(consumer_worker)
    consumer_worker.start()

while 1:
    control_process = raw_input('> Y/N: ')
    if control_process == 'Y':
        for producer in producer_pool:
            producer.running = False
            # Joining this to make sure all the producers die
            producer.join()

        for consumer in consumer_pool:
            # Ideally consumer should stop once producers die
            consumer.producer_alive = False

        break
