import math
def tryelse():
    print("this program finds the real solution to a quadratic\n")
    try:#接程序执行的语句（可看作没有）
        a,b,c=eval(input("please enter the coefficients(a,b,c):"))
        discRoot = math.sqrt(b * b - 4 * a * c)
        root1 = (-b + discRoot) / (2 * a)
        root2 = (-b - discRoot) / (2 * a)
        print("\nthe solutions are:", root1, root2)
    except ValueError as exc0bj:#值错误
        print(exc0bj)
        if str(exc0bj)=="math domain error":
            print("no real roots")
        else:
            print("didn't give the right number of coefficients")
    except NameError:#试图访问的变量名错误
        print("\ndidn't enter 3 numbers")
    except TypeError:#参数类型错误
        print("\ninputs were not all numbers")
    except SyntaxError:#语法错误，代码形式错误
        print("\ninput was not in the correct form")
    except:
        print("wrong,sorry")
tryelse()
