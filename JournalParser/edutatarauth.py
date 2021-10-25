"""A part of this code was provided by Ramil Aglyamzanov"""

import requests

def edu_auth(login, password):
    s = requests.Session()

    s.headers.update({"Host": "edu.tatar.ru",
                      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                                    "Chrome/89.0.4389.90 Safari/537.36"
                      })
    h = {"Referer": "https://edu.tatar.ru/logon",
         }

    r = s.post("https://edu.tatar.ru/logon", headers=h,
               data={
                   "main_login2": login,
                   "main_password2": password}
               )

    if 'Личный кабинет' in r.text:
        print('Успешный вход в аккаунт.')
    else:
        raise PermissionError('Не удалось войти в аккаунт. Убедитесь, что вы верно ввели логин/пароль и двухфакторная аутентификация отключена.')

    return s