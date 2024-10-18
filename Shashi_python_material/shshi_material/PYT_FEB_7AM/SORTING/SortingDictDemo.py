





#sorted(iterable,key=None,reverse=False) -> list
d={"c":"cnu","d":"dhanu","a":"amma","b":"brother"}
print("Dict : ",d)

sk=sorted( d.keys() )
sv=sorted( d.values( ) )

d=dict( zip(sk,sv) )   #zip(iterable,iterable) -> zip object | iterable
print("Sorted dict : ",d)



