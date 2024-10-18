
import sys
import time

print("Prg Name is : ",sys.argv[0])
#print("Command Line arg : ",sys.argv)

for i in sys.argv[1:]:
    time.sleep(.5)
    print(i)
