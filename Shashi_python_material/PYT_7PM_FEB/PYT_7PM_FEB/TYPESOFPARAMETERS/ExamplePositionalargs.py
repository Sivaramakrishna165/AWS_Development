
Types Of Parameters
 1.Positional arguments
      - By default all the formal parameters
      are acts positional arguments only.

      - In this case order and count of parameters
      must be maintained.
      
 2.keyword arguments
     - By Default all formal parameters also acts
     keyword arguments.

     - But in this case order is not mater but count is mater
     - In this case have to pass the value to formal parameter
     by using their names.

 3.Positional only arguments
      - If any parameters which are declare left side
      of / parameter called positional only arguments.

      - In this case order and count must be maintained.

          def myFun(x,y,/):
              pass   

 
 4.Keyword only arguments
      - If any argument which are declare
      right side of * parameter

      - in this case we have to pass the values by
      using their names

      - in this case count of the parameters mater.

          def myFun(*,x,y):
              pass

 5.Default parameter
        - Process of defining the formal parameter
        by with some values

        - Default parameters acts as optional parameter
        - Default parameters are replaced by actual
        parameter
        - Defaul parameters are takes place whenever
        we fail to pass the values that parameter
    
  6.varargs parameters
        - Process of defining the formal parameter
        with * operator

               def myFun(*,x):  x is acts as keyword only arg               
                   pass

                def myFun(*x):  *x is acts varargs
                      pass

        - varargs can take 0 to N no.of.positional only
        arguments.

        - varargs internally acts a tuple

   7.kwargs parameters
         - If any parameter which are declared by using **
         - Internally works as dict collection.
         - It can take 0 to N no.of.Keyword only arguments













