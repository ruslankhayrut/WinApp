"""A part of this code was provided by Ramil Aglyamzanov"""

import requests

def edu_auth(login, password):
    s = requests.Session()

    s.headers.update({"Host": "edu.tatar.ru",
                      "Origin": "https://edu.tatar.ru",
                      "User-Agent": "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) \
                                        AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 \
                                        YaBrowser/18.10.1.382 (beta) Yowser/2.5 Safari/537.36"
                      })
    h = {"Referer": "https://edu.tatar.ru/start/logon-process", "Content-Type": "application/x-www-form-urlencoded"}

    r = s.post("https://edu.tatar.ru/logon", headers=h,
               data={
                   "redirect_url": "https://edu.tatar.ru/start/logon-process",
                   "main_login": login,
                   "main_password": password}
               )
    if 'Личный кабинет' in r.text:
        print('Успешный вход в аккаунт.')
    else:
        raise PermissionError('Не удалось войти в аккаунт. Убедитесь, что вы верно ввели логин/пароль и двухфакторная аутентификация отключена.')

    return s