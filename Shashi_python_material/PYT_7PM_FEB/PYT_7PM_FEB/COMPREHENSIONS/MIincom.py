




#comprehensions
#Syn: [ <exp> for variable in iterable for v in iterable if test ]

lst_sm=["sai","james"]
lst_p=["pens","markers","books"]

lst_r=[(i,j) for i in lst_sm for j in lst_p if j=="markers"]
print("Result : ",lst_r)


      





