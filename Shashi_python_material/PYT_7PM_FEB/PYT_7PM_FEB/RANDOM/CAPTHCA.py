
''' First 2 digits
    3rd upper case letter
    4 and 5 digits
    6th lower case letter '''

import time
import random

for i in range(1,11):
    time.sleep(.2)
    print(random.randint(11,99),
    chr(random.randint(65,90)),
    random.randint(11,99),
    chr(random.randint(97,122)),sep='')






    
