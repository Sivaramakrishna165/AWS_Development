



import time
t=( [11,22,33], (1.1,2.2,3.3),
         {"aaa","bbb","ccc"},
         {"sno":101,"sname":"sai","scity":"hyd"}
    )

for i in t:
    if isinstance(i,tuple):
        print("tuple data ",i)
        for j in i:
            time.sleep(.2)
            print(j)

t[3].update({"sname":"samatha"})
print("dict : ",t[3])








            

