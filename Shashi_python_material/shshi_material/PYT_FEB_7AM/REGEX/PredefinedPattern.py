



import re
import time

citr=re.finditer("\S","AbC 1#d*[ m n W67")

for m in citr:
    time.sleep(.2)
    print("Match : ",m.group()," Found @ : ",m.start())    



''' Predefined Patterns

     \d  ----> only digits
     \D    --> Except Digits

     \s   --> Only Space
     \S   --> Except Spaces

     \w   --> A|N
     \W  --> Except A|N

     ^  ---> Pattern Starts with
     $  --> Pattern Ends with ....

'''


     




     

     
