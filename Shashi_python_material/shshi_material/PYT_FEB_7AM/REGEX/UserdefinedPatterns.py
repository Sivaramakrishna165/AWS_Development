



import re
import time

citr=re.finditer("[^a-zA-Z0-9 ]","AbC 1#d*[ m n W67")

for m in citr:
    time.sleep(.2)
    print("Match : ",m.group()," Found : ",m.start() )


''' Userdefined Patterns

     a  --> it will search for only a
     [abc] --> Either a or b or c
     [^abc] --> Except a or b or c

     [a-z]  ---> It search for only lower case letters
     [A-Z] ---> Only Upper Case letters
     [a-zA-Z] --> It will sarch only alpha

     [^a-zA-Z] --> Except Alpha
     [0-9] or \d ---> only digits
     [a-zA-Z0-9] or \w ---> A|N

'''





     






     
     




     




     

     
