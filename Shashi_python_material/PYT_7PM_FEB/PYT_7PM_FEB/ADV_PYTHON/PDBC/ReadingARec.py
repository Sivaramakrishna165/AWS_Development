
import cx_Oracle

conn=None
cur=None

try:
    conn=cx_Oracle.connect("scott","tiger","localhost:1521/orcl5")
    
except cx_Oracle.DatabaseError as e:
    print("Sorry Unable to continue...")
    print("Reason : ",e)
    
else:
    print("Connection is Est ")
    cur=conn.cursor()
    print("Cursor object is Created ")

    query="SELECT EMPNO,ENAME,JOB FROM EMP"
    cur.execute(query)

    t=cur.fetchone()
    print("Record : ",t)

finally:
    if cur!=None:
        cur.close()

    if conn!=None:
        conn.close()




