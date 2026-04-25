# Многофункциональный бот для загрузки аудио/видео материалов с популярных площадок
Большинство файлов скачиваются через yt-dlp

### Краткая настройка config.json
{
    "bot_token": "BOTFATHER_TOKEN", # получение токена из офиц. бота тг @BotFather
    "yandex_token": "TOKEN", # токен яндекс
    "proxies": [
      #сюда можно добавлять socks5 прокси (на гитхабе их много)
    ],
    "db_name": "users.json" - #имя бд
}

### чтобы получить yandex_token, нужно перейти по ссылке
https://oauth.yandex.ru/authorize?response_type=token&client_id=23cabbbdc6cd418abb4b39c32c41195d
и при авторизированной странице из
https://music.yandex.ru/#access_token=y0__{токен яндекса}&token_type={}&expires_in={}&state={}cid={}


Для запуска хватит обычной картошки))
