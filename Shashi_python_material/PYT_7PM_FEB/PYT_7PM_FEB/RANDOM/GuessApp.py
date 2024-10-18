
import time
import random

lst=['django','python','java','mongodb','dm']

for i in range(1,11):
    item=random.choice(lst)
    guess=input("Guess the course : ")

    if guess==item:
        print("Congrats ... u won the course...",guess)
        break
    else:
        time.sleep(.3)
        print("Try again ")
        
