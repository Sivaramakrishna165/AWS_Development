




import cx_Oracle

conn=cx_Oracle.connect("scott","tiger","localhost:1521/orcl5")

if conn!=None:
    print("Connection is Est ")
    
    cur=conn.cursor()
    print("cursor object is created ")

    query="CREATE TABLE PYT7AM(SNO NUMBER(3),SNAME VARCHAR(10),SCITY VARCHAR(10))"
    cur.execute(query)
    print("Table is created ")

    cur.close()
    conn.close()    
        
else:
    print("Connection is Fail")




