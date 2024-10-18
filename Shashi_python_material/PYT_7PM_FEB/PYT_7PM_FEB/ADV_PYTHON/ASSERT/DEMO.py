import time
#assert <condition>,'Message'

def sq(x):
    s=x*x
    return s

#calling
time.sleep(2)
assert sq(2)==4,"sq(2) should be 5 only"
print("Result of sq(2) ? : ",sq(2))

time.sleep(2)
assert sq(3)==9,"sq(3) should be 9 only"
print("Result of sq(3) ? : ",sq(3))

time.sleep(2)
assert sq(4)==16,"sq(4) should be 16 only"
print("Result of sq(4) ? : ",sq(4))

