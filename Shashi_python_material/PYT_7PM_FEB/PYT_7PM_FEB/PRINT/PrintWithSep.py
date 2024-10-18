x=10
y=12.12
z="SssiT"

print(x,y,z) #Output: 10 12.12 SssiT
print(x,y,z,sep=' ') #Output:10 12.12 SssiT
print(x,y,z,sep=",") #Output:10,12.12,SssiT
print(x,y,z,sep='-')
print(x,y,z,sep='')


'''Note: While printing multiple values using a print( )
then each value is sep by a space by default

Reason is : default value for sep attribute | property
in print( ) is a space
                     print(sep=' ')

Based on the application req we can set any literals
as a sep
'''
