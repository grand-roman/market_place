# market_place_proj
Интернет-магазин

Требования
===

- Python 3.9+
- Django 3.2.8
- Celery
- RabbitMQ
- Redis

Установка
===

- Деплой приложения на сервер. Linux пакеты устанавливаются скриптом install/install.sh
- Установка зависимостей `pip install -r requirements.txt`
- Проверьте владельца папки с приложением и права
- Настройка .env `copy .env.dist .env`
- запуск приложения, 
- запуск "nohup python manage.py rabbit > /dev/null 2>&1 &" (от имени владельца с активированным venv) 
- запуск "nohup celery -A market_place_proj worker -l info > /dev/null 2>&1 &" (от имени владельца с активированным venv)

## Built With

* [Django](https://www.djangoproject.com/) -  web framework written in Python.
* [Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/en/latest/) - A configurable set of panels that display various debug information about the current request/response.
* [Django Environ](https://pypi.org/project/django-environ/) - Configure Django made easy.
* [Django MPTT](https://django-mptt.readthedocs.io/en/latest/) - Utilities for implementing Modified Preorder Tree Traversal with your Django Models and working with trees of Model instances.
* [Django-modeltranslation](https://django-modeltranslation.readthedocs.io/en/latest/) - Battery for translating models.
* [Django View Breadcrumbs](https://github.com/tj-django/django-view-breadcrumbs) - Provides a set of breadcrumb mixin classes that can be added to any django view.
* [Flake8](https://flake8.pycqa.org/en/latest/index.html#) - Your Tool For Style Guide Enforcement.
* [Flake8 isort](https://pypi.org/project/flake8-isort/) - Use isort to check if the imports on your python files are sorted the way you expect.
* [Django Extensions](https://github.com/django-extensions/django-extensions) - Django Extensions is a collection of custom extensions for the Django Framework.
* [Faker](https://faker.readthedocs.io/en/master/n) - Faker is a Python package that generates fake data for you.
* [Django Model Utils](https://django-model-utils.readthedocs.io/en/latest/setup.html#installation) - Django model mixins and utilities.
* [Django-autoslug](https://pypi.org/project/django-autoslug/) - Django-autoslug is a reusable Django library that provides an improved slug field.
* [Django REST framework](https://www.django-rest-framework.org/) - Django REST framework is a powerful and flexible toolkit for building Web APIs. 
* [RabbitMQ](https://www.rabbitmq.com/) - RabbitMQ is the most widely deployed open source message broker.
* [tqdm](https://pypi.org/project/tqdm/) - Simple progressbar

## Make команды

* **run** - запуск сервера разработки.
* **migrate** - синхронизация состояние базы данных с текущим состоянием моделей и миграций.
* **files** - инициализация статических файлов.
* **messages** - сбор сообщений для переводов.
* **translate** - компиляция сообщений для переводов.
* **test_data** - генерация тестовых данных.
* **translate** - выполнение локализации.
* **rabbit** - запуск симуляции сервиса оплаты товара.
* **pay** - команда оплаты товара.
