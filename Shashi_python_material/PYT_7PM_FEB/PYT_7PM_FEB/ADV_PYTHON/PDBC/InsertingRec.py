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
    print("Cursor object is created ")

    query="INSERT INTO PYTSTUINFO VALUES(111,'SHASHI','HYD')"
    cur.execute(query)
    print("Rec is inserted")
    conn.commit()

finally:
    if cur!=None:
        cur.close()

    if conn!=None:
        conn.close()



