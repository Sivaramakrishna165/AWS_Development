




#filter(func or None , iterables ) -> filter object | iterable
lst_comm=[None,300,500,0.0,1400,"",None,0,0+0j]
r=list(filter(None , lst_comm))
print("Result is : ",r)
print(len(r))
