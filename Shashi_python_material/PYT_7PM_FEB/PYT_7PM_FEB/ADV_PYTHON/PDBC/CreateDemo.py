
''' To Create a table in the scott
with pytstuinfo [sno|sname|scity '''

import cx_Oracle

conn=cx_Oracle.connect("scott","tiger","localhost:1521/orcl5")

if conn!=None:
    print("Connect is Est ")

    cur=conn.cursor()
    print("cursor object is created ")

    query="CREATE TABLE PYTSTUINFO(SNO NUMBER(3),SNAME VARCHAR(10),SCITY VARCHAR(10))" 
    cur.execute(query)
    print("Table is Created ")

    cur.close()
    conn.close()
    
else:
    print("Connect is Fail")
