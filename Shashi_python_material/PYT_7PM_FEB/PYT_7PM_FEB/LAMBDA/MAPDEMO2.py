


import time

#map(func,*iterable) -> map object | iterable
lst_rad=[2,3.3,4.56,2.2]
area=tuple( map(lambda rad: 3.14*rad*rad ,lst_rad ) )

for i in area:
    time.sleep(.2)
    print("%.2f" %i)
