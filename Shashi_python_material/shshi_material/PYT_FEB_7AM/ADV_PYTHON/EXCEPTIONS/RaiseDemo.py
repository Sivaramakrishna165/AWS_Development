
''' Accept age from the user
print major if age>=21 else
raise ZeroDivisionError to display
minor ...

syn: raise <ExceptionClsName>([list of args])
'''

age=int(input("Enter age : "))

if age>=21:
    print("Major")
else:
    try:
        raise ZeroDivisionError()
    except ZeroDivisionError:
        print("ZDE : Minor")
        
    






