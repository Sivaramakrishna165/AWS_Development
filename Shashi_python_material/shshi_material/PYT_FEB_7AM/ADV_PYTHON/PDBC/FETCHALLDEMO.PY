
import cx_Oracle
import time

conn=None
cur=None

try:
    conn=cx_Oracle.connect("scott","tiger","localhost:1521/orcl5")    

except cx_Oracle.DatabaseError as e:
    print("Connection is Failed ")
    print("Reason : ",e)

else:
    print("Connection is Est ")

    cur=conn.cursor()
    query="SELECT empno,ename,job from emp where job='%s'"
    jobtitle=input("Enter job title : ").upper()
    cur.execute(query %jobtitle)

    lst=cur.fetchall()
    for t  in lst:
        time.sleep(1)
        for i in t:
            print(i,end='\t')
        print(" ")    

finally:
    if cur!=None:
        cur.close()

    if conn!=None:
        conn.close()







        

