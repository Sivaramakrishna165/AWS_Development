
''' Accept a character from the user
findout the given char is vowel or not '''
ch=input("Enter any char ") 
lst=['A','a','E','e','I','i','O','o','U','u']

'''
if ch=='a' or ch=='e' or ch=='i' or ch=='o' or ch=='u' or
ch=='A' or ch=='E' or ch=='I' or ch=='O' or ch=='U':
    print("vowel")
else:
    print("Not vowel") 
'''
#if ch in lst:
if ch in "AaEeIiOoUu":
    print("Vowel")
else:
    print("not vowel")

    
    
