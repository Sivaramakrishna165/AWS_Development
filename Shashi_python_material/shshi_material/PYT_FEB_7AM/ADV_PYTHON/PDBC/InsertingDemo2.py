''' syn:
INSERT into <tablename>
values (value1,value2,....value n) '''

import cx_Oracle

conn=None
cur=None

try:
    conn=cx_Oracle.connect("scott","tiger","localhost:1521/orcl5")

except cx_Oracle.DatabaseError as e:
    print("sorry Unable to continue...")
    print("Reason is : ",e)

else:
    print("connection is Est ")
    
    cur=conn.cursor()
    print("cursor object is created ")

    query="INSERT INTO PYT7AM VALUES(%d,'%s','%s')"
    
    while True:
        sno=int(input("Enter sno : "))
        sname=input("Enter sname : ")
        scity=input("Enter scity : ")
    
        cur.execute(query %(sno,sname,scity))
        print(cur.rowcount," Rec is inserted ....")
        conn.commit()

        opt=input("Do u want another Rect Y|N ")
        if opt in ['N','n']:
            break        

finally:
    if cur!=None:
        cur.close()

    if conn!=None:
        conn.close()


