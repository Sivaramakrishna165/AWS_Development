
''' Esc SEQ Character
       used to produce the result in the
                             user desired fashion

        * also know back slash character

        Back Slash char               Resp
        ==========================
        \n                                      new line
        \b                                      back space
        \a                                      bell sound
        \t                                       H.Tab space

        \'                                       It will print ' sym
        \"                                      It will print " sym
        \\                                       It will print \ sym

Note: we can use in print( ) directly or
we can use them as value of end and sep attribute
in print( )
'''

print("welcome") #end='\n'
print("\n to") #end='\n'
print("\n sssit") #end='\n'
print("welcome \n to \n SssiT")
print("========================")

x=10
y=12.12
z="SssiT"

print(x,"\t",y,"\t",z,sep='')
print(x,y,z,sep='\t')

print("==========================")
print(x)
print(y)
print(z)

print(x,"\n",y,"\n",z)
print("=========================")
print(x,y,z,sep='\n')































        
        
