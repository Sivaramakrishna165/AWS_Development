


Types of Formal paramters :
    1.Positional arguments
       - By default all formal parameters are acts
       positional arguments.
       - In This case order and count of arguments
       must be maintained.
       
    2.Keyword arguments
        - By Default all formal parameters are acts
        as keyword as well

        - here we have to pass the values to the
        formal parameter by using their names.

        - In this case order is not matter where as
        count of the parameters are matters.
        
    3.Positional only arguments
         - The Parameters which are
         declared left side of  / parameters

         - In This case order and count of the parameters
         need to be maintained.

             def myFun(x,y,/):
                 pass
         
    4.Keyword only arguments
         - The parameters which are declare
         right side of * parameter
                 def myFun(*,x,y):
                     pass

           - in this case order is not matter but count is
           matter

           - In this case we have to pass the values to
           parameter using their names
           
    5.Default arguments
           - Process of defining the formal parameters
           with some values.

           - Default parameters are acts as optional
           parameters.

           - Default parameters are takes place whenever
           we fail to pass the values to default parameter.

           - Default parameters are replaced by actual
           arguments

   
    6.Varargs
         - If any parameter which are declared by using *
              def myFun(*,x,y): #Keyword only arg
                  pass

               def myFun(*x): #varargs | variable length arg
                   pass

        - varargs are acts as optional parameter
        - varargs can take 0 to N no.of.positional only
                                                                         arguments.
        - varargs internally works as a tuple collection.











    
    7.kwargs parameter

















