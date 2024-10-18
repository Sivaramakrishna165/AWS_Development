
import cx_Oracle,time

conn=None
cur=None

try:
    conn=cx_Oracle.connect("scott","tiger","localhost:1521/orcl5")

except cx_Oracle.DatabaseError as e:
    print("Sorry unable to continue....")

else:
    print("Connection is Est ")
    cur=conn.cursor()
    print("cursor object is created ")

    jobt=input("Enter Job Title : ")
    query="select empno,ename,job,sal
                             from emp where job='%s'"
    cur.execute(query %jobt)

    for t in cur:
        time.sleep(.2)
        for i in t:
            time.sleep(.2)
            print(i,end='\t')
        print(" ")

    '''
    lt=cur.fetchall()
    for t in lt:
        time.sleep(.2)
        for i in t:
            time.sleep(.2)
            print(i,end='\t')
        print(" ")
    '''
    
finally:
    if cur!=None:
        cur.close()

    if conn!=None:
        conn.close()

