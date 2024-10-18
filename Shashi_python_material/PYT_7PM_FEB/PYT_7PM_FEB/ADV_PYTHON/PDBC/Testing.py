#Testing Connection

import cx_Oracle

conn=cx_Oracle.connect("scott","tiger","localhost:1521/orcl5")

if conn!=None:
    print("Connect is Est")

    cur=conn.cursor()
    print("cursor object is created ")
    
else:
    print("Connect is Fail")
