
'''
Exception are classified into 2 types
  1.Predefined Exception
  2.Userdefined Exception
          Every Exception is a class.

    Syn: raise <ExceptionClsName>([list of args])

Accept age from the user print Major iff age>=21
else raise the ZeroDivisionError and display
Invalid Age Group
'''

age=int( input("Enter age : ") )

if age>=21:
    print("Major ")
else:
    try:
        raise ZeroDivisionError()
    except ZeroDivisionError:
        print("ZDE : Invalid Age Group ")





















