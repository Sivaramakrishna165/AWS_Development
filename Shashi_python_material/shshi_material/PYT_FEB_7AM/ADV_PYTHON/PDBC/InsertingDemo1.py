''' syn:
INSERT into <tablename>
values (value1,value2,....value n) '''

import cx_Oracle

cur=None
conn=None

try:
    conn=cx_Oracle.connect("scott","tiger","localhost:1521/orcl5")

except cx_Oracle.DatabaseError as e:
    print("Sorry unable to continue....")
    print("Reason : ",e)

else:
    print("Connection is Est")
    cur=conn.cursor()
    print("cursor object is created ")

    query="INSERT INTO PYT7AM VALUES(101,'ANU','HYD')"
    cur.execute(query)
    print("Rec is inserted....")
    conn.commit()

finally:
    if cur!=None:
        cur.close()

    if conn!=None:    
        conn.close()
    




