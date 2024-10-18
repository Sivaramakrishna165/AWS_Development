import cx_Oracle
conn=None
cur=None

try:
    conn=cx_Oracle.connect("scott","tiger","localhost:1521/orcl5")

except cx_Oracle.DatabaseError as e:
    print("Sorry unable to continue....")
    print("Reason : ",e)

else:
    print("Connection is Est ")
    cur=conn.cursor()
    print("cursor object is created ")

    query=
    "UPDATE EMP SET SAL=SAL+%d WHERE job='%s'"

    incsal=int(input("Enter increment Salary : "))
    job_title=input("Enter Job_Title : ")
    
    cur.execute(query %(incsal,job_title) )
    conn.commit()
    print(cur.rowcount," Rows updated ....!")
                
finally:
    if cur!=None:
        cur.close()

    if conn!=None:
        conn.close()
