from requests import Session
import os


getUrl = 'http://218.197.150.140/servlet/GenImg'
postUrl = 'http://218.197.150.140/servlet/Login'

codepage = Session()

try:
    os.mkdir('./trainData/')
except:
    FileExistsError

while True:
    response1 = codepage.get(url=getUrl)

    with open('tmp.jpg', 'wb') as f:
        f.write(response1.content)

    code = input('Enter the code: ')

    response2 = codepage.post(
        url=postUrl, data={'id': '', 'pwd': '', 'xdvfb': code})

    if '验证码错误' not in response2.text:
        with open('trainData/{code}.jpg'.format(code=code), 'wb') as f:
            f.write(response1.content)
