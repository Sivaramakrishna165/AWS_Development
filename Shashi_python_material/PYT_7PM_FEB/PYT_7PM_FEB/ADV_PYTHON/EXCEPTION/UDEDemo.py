
''' User Defined Exception
       - The Exception class which is
       defined by us for our application
       req.

       - Defining an exception class is nothing but
       creating sub class of  class  Exception
       
             class Sample:   Normal Class
                  pass

             class Sample(Exception):   ExceptionClass
                     pass

       - def a parameterized constructor in the
       Exception Class for displaying Exception
       classname and description.

       - Based  on the application req, we have
       to raise that exception Explicitly '''

class MyLoginException(Exception):
    def __init__(self,msg):
        self.msg=msg

'''Application'''
un=input("Enter username : ")
pw=input("Enter password : ")

if un=="sssit" and pw=="kphb":
    print("Valid user ")
else:
    try:
        raise MyLoginException('Invalid UN OR PW...')
    except MyLoginException as e:
        print("Sorry Unable to continue....")
        print("Reason : ",e)




        










  
