
import time

n=input("enter any char ") #sai

for i in n:
    time.sleep(.2)
    if i=='a' or i=='e' or i=='i' or i=='o' or i=='u':
        continue
    print(i)
    
