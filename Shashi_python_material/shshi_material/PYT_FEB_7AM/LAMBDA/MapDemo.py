




# map(func,*iterables) -> map object | iterable

lst=[1,2,3]
lst2=[]

def sq(x):
    s=x*x
    return s

''' App-1
for i in lst:
    r=sq(i)
    lst2.append(r)
print("Result is : ",lst2)   '''

'''
#App-2
m=map(sq,lst)
lst2=list(m)
print("Result is : ",lst2) '''

m=map( lambda x: x*x, lst)
lst2=list(m)
print("Result is : ",lst2)

print("Result is : ",  list( map(lambda x: x*x, lst) ) )















    






    


