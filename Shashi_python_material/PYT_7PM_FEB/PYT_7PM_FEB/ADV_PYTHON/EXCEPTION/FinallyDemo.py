
import time

try:
    time.sleep(1)
    print("*** Try *** ")
    print(" 1 ")
    print(" 2 ")
    raise IndexError()

except ValueError:
    time.sleep(1)
    print("*** Except *** ")
    print(" 4 ")
    print(" 5 ")

else:
    time.sleep(1)
    print("*** Else *** ")
    print(" 6 ")
    print(" 7 ")

finally:
    time.sleep(1)
    print("*** Finally *** ")
    print(" 8 ")
    print(" 9 ")

time.sleep(1)
print("*** Outside of Finally *** ")
print(" 10 ")
print(" 11 ")
    
    
    
    
    
