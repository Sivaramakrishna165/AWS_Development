import cx_Oracle
import time

conn=None
cur=None

try:
    conn=cx_Oracle.connect("scott","tiger","localhost:1521/orcl5")

except cx_Oracle.DatabaseError as e:
    print("Sorry Unable to continue....")

else:
    print("Connection is Est ")
    cur=conn.cursor()
    print("cursor object is Created ")

    cur.execute("SELECT empno,ename,job from emp")
    lt=cur.fetchmany(5)

    for t in lt:
        time.sleep(1)
        for i in t:
            time.sleep(.2)
            print(i,end="\t")
            
        print(" ")

finally:
    if cur!=None:
        cur.close()

    if conn!=None:
        conn.close()
