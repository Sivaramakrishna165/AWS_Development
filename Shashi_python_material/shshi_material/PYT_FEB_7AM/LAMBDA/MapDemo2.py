
#map(func,*iterable) -> map object

lst_rad=[2, 3.3, 4.12]

t=tuple( map( lambda rad: 3.14*rad*rad ,lst_rad) )
print("Result is : ",t)
