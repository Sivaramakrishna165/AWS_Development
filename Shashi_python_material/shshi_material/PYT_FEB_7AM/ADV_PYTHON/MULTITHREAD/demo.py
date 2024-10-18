
Multi-Tasking
  Process Based MT
  Thread Based MT
      Java | .net | Android | Python

threading module
  Ways to define Threads
    1.Defining the thread by using an already existed
        Function

        thread(target,args,name) -> Thread object
           target : Name of the Function or Name of
                                                                  the method
          args : arguments which are req for function
                                                                        or method

          name: name For Thread
               args and name parameters are optional

    2.Defining the Thread by creating non sub class
    of Thread

    3.Defining the Thread by creating sub class of
    Thread.

    import threading
    class Cat(threading.Thread):
        pass

    Whatever the logic u want as thread then that logic
    must be defined inside of run( ) of Thread class.

    - run( ) thread class should not be explicitly
    - run( ) thread class should be called by start( )
    of thread class.    

    Note: After defining the thread we start the execution
    of the threads by using start( ) from thread class.
    ========================================

    Note: Default thread in Python is main Thread
    and main thread is automatically executed Thread
    By the OS

    =========================================

    Note: Whenever u define any thread by default
    every thread is created with their default name.
    like thread-1 | thread-2 .....

    we can get or set the name of the Thread
    by using name property of thread

    =============================================

    How to get the object of current working thread ?
    by using current_thread( ) from threading module.





       




    
    







    

   
