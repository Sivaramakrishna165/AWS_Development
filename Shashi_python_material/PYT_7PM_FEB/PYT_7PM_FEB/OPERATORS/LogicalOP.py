'''

Logical Operators

x,y,z=10,20,30

if x>y and x>z then x is big
if y>x and y>z then y is big
if z>x and z>y then z is big

Logical Operators are
    In Other Languages and - &&
                                             or  - ||
                                            not - !
                                            
    In Python and | or  | not
                   and
    exp1     exp2      Result
    True     False     False
    False    True      False
    False    False    False
    True     True      True

                    or
    exp1     exp2      Result
    True      False     True
    False    True      True
    False    False     False
    True     True      True   '''

x,y,z=10,20,30

print("x>y and x>z ? : ",   x>y and x>z) #F and F -> False
print("z>x and z>y ? : ",   z>x and z>y) #T and T -> True
print("================================")

print("y>x or y>z ? : ", y>x or y>z) #T or F ->True
print("z>x or z>y ? : ", z>x or z>y) #T or T -> True

print("========================")

x=10
y=20
z=x>y #False
a=not x>y #not False -> True
print("z Result is : ",z)
print("a result is : ",a)









    
