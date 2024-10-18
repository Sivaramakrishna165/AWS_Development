
''' Accept 3 subject marks
    findout total,avg,result and grade
        pass marks > 34 in all subjects
           if Result is pass then check the avg
               if avg>=70 print Grade A
               if avg>=60 print Grade B
               if avg>=50 print Grade C else Grade '''

m1=int(input("Enter m1 : "))
m2=int(input("Enter m2 : "))
m3=int(input("Enter m3 : "))

tot=m1+m2+m3
avg=tot/3

print("total is : ",tot)
print("Avg is : ",avg)

if m1>34 and m2>34 and m3>34:
    print("Result is PASS")
    if avg>=70:
        print("GRADE-A")
    elif avg>=60:
        print("GRADE-B")
    elif avg>=50:
        print("GRADE-C")
    else:
        print("GRADE-D")
else:
    print("Result is : Fail")













               
              
