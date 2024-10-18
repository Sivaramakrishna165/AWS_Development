
''' accept username and password
from the user findout the user is valid
or not

 username should be sssit 
 password should be kphb  '''

class MyLoginException(Exception):
    def __init__(self,msg):
        self.msg=msg

#actual code
un=input("Enter username : ")
pw=input("Enter password : ")

if un=="sssit" and pw=="kphb":
    print("Valid user ")
else:
    try:
        raise MyLoginException('Invalid UN or PW... !!!')
    
    except MyLoginException as e:
        print("Sorry Unable to continue....")
        print("Reason : ",e)









