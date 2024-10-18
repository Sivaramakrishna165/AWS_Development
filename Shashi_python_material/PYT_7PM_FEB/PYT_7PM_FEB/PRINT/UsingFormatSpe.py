
''' Working with Format Specifiers
    in the print( )

   Data type    format specifiers
    int          ---->              %d     Eg:   12123 | -2345
    float      ----->             %f      Eg:    12.12 | -12.3434
    str         ----->             %s      Eg:    's' | "shashi"

    Syn: print("format specifier" %variable)
         print("format specifiers" %(variables) )   

'''
x=10
print("%d" %x) #output: 10
print("x val is : %d" %x) #Output: x val is : 10
print("===================")

y=12.12
print("%f" %y)
print("%.2f" %y)
print("==================")

print("%d%f" %(x,y))
print("%d\t%f" %(x,y))
























