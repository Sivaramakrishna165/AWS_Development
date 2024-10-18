
import time
import random

lst=["pen","book","cpu","mouse"]

for i in range(1,11):
    time.sleep(.5)
    item=random.choice(lst)
    print(item)
