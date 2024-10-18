Ways to define the threads :
===========================
    
1. Defining thread by using an already
                                                  existed Fun

Thread(target,args,name) -> Thread object from
threading module.

target : Name of the function u want make it as thread
args: it should be tuple if function req any arg
name : attribute is ment for assign the name for thread

Note : After defining the threads we have to call
start( ) of thread class for executing the Threads

2.Defining the Thread by creating non sub class
of Thread
============================================
Thread(target,args,name) -> Thread object from
threading module.

3.Defining the Thread by creating sub class of
Thread.

class Sample:
    pass

class Sample(ABC):
    pass

class Sample(Exception):
    pass

import threading
class Sample(threading.Thread):
    pass

If u want execute any logic as thread then
that logic must be defined inside of run( ) of
thread class.

run() of thread class shouldn't call explicitly
it should be called by start() thread class.


















