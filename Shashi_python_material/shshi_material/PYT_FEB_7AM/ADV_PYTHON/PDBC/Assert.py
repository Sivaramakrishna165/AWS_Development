import time
def sq(x):
    s=x*x
    return s

#calling
assert sq(2)==4,"sq(2) should be 4 But not ...."
time.sleep(1)
print("Result is ",sq(2))

assert sq(3)==9,"sq(3) should be 9 But not ...."
time.sleep(1)
print("Result is : ",sq(3))

assert sq(4)==16,"sq(4) should be 16 But Not...."
time.sleep(1)
print("Result is : ",sq(4))



#assert condition,message
