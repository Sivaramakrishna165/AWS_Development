
import cx_Oracle

conn=cx_Oracle.connect("scott","tiger","localhost:1521/orcl5")

if conn!=None:
    print("connection is Est ")
else:
    print("connection is Failed")
