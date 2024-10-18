
''' Reading the first 5 Rec from emp '''

import cx_Oracle,time

conn=None
cur=None

try:
    conn=cx_Oracle.connect("scott","tiger","localhost:1521/orcl5")

except cx_Oracle.DatabaseError as e:
    print("Connection is Failed ")
    print("Reason is : ",e)

else:
    print("Connection is Est ")

    cur=conn.cursor()
    print("cursor object is created ")

    query="SELECT EMPNO,ENAME,JOB FROM EMP";
    cur.execute(query)

    lst=cur.fetchmany(5)
    for t in lst:
        for i in t:
            time.sleep(.2)
            print(i,end='\t')
        print(" ")        

finally:
    if cur!=None:
        cur.close()

    if conn!=None:
        conn.close()







