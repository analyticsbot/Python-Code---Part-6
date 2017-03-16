from multiprocessing import Manager, Process, Pool,Queue
from Queue import Empty

def writer(queue):
   for i in range(10):
     queue.put(i)
     print 'put %i size now %i'%(i, queue.qsize())

def reader(id, queue):
   for i in range(10):
     try:
       cnt = queue.get(1,1)
       print '%i got %i size now %i'%(id, cnt, queue.qsize())
     except Empty:
       pass

class Managerss:
   def __init__(self):
     self.queue= Queue()
     self.NUMBER_OF_PROCESSES = 4

   def start(self):
     self.p = Process(target=writer, args=(self.queue,))
     self.p.start()
     self.workers = [Process(target=reader, args=(i, self.queue,))
                        for i in xrange(self.NUMBER_OF_PROCESSES)]
     for w in self.workers:
       w.start()

   def join(self):
     self.p.join()
     for w in self.workers:
       w.join()

if __name__ == '__main__':
    m= Managerss()
    m.start()
    m.join()
