
''' tuple is immutable collections
       thus in the tuple there is no
          append( ) | insert( ) | extend( ) |
          copy( ) | remove( ) | pop( ) | clear( ) |
          reverse( ) | sort( )

          index( ) | count( ) are existed in the tuple

   > Can u insert an item @ specified index
   > Can u update an existed item existed @ specified
                                             Position
   > Can u delete an item @ given position
'''

t1=()
print("tuple : ",t1)

t2=(10,12.12,"shashi",None,10)
print("tuple : ",t2)

t3=10,12.12,"chinni","khanna" #packing
print("type is : ",type(t3))
print("tuple is : ",t3)
print("======================")

t4=(10,) #t4=10,
print("type is : ",type(t4))
print("tuple is : ",t4)
print("======================")

#tuple( ) -> empty tuple
t5=tuple( )
print("data is : ",t5)
print("======================")

#tuple(iterable) -> tuple
lst=[10,20,30,40,50,"anu","aishu","manu"]
t6=tuple(lst)
print("data is : ",t6)
print("======================")

s="SAI"
t7=tuple(s)
print("data is : ",t7)




































