*Учебный проект для автоматического тестирования резервного копирования и восстановления базы данных Firebird с помощью gbak.*


Основные инструменты проекта:

- Python
- pytest
- firebird-qa
- firebird-driver
- gbak


## Что проверяется

- создание тестовой базы средствами Firebird QA;
- создание таблиц, ограничений и индексов;
- заполнение таблиц тестовыми данными;
- создание резервной копии с помощью `gbak`;
- восстановление копии в отдельный файл базы данных;
- проверка данных и индексов после восстановления.


## Требования

- macOS;
- установленный и запущенный Firebird Server;
- Python 3.8 или новее;
- доступные утилиты Firebird, включая `gbak`;
- учётная запись Firebird с правами на создание тестовых баз.
- готовый firebird-driver.conf



## Установка на macOS

Создайте виртуальное окружение:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Установите зависимости:

```bash
pip install -r requirements.txt
```

Откройте `firebird-driver.conf` и укажите параметры своего локального сервера Firebird:

```ini
[local]
host = localhost
port = 3050
user = SYSDBA
password = masterkey
```

Запустите тесты:

```bash
pytest
```

Firebird QA добавляет в pytest параметр `--server`, а `pytest.ini` уже задаёт `local`.

Для подробного вывода:

```bash
pytest -v
```

Мой вывод:
<img width="1454" height="709" alt="image" src="https://github.com/user-attachments/assets/b47f2eb0-fa76-4824-9a63-6a6b2b9c1dbc" />

