run:
	python market_place_proj/manage.py runserver
migrate:
	python market_place_proj/manage.py makemigrations
	python market_place_proj/manage.py migrate
superuser:
	python market_place_proj/manage.py createsuperuser
files:
	python market_place_proj/manage.py collectstatic
shell:
	python market_place_proj/manage.py shell
test_data:
	python market_place_proj/manage.py clear_cart
	python market_place_proj/manage.py fake_users
	python market_place_proj/manage.py fake_stocks
	python market_place_proj/manage.py loaddata app_market
	python market_place_proj/manage.py wonderful_seller
	python market_place_proj/manage.py catalog
	python market_place_proj/manage.py loaddata discount_variants
	python market_place_proj/manage.py discounts
	python market_place_proj/manage.py cart_sale
	python market_place_proj/manage.py tags
test:
	pytest
lint:
	isort --recursive .
	flake8 market_place_proj
start:
	python market_place_proj/manage.py migrate
	python market_place_proj/manage.py createsuperuser
	# python market_place_proj/manage.py collectstatic
messages:
	django-admin makemessages -l ru --ignore=static --ignore=media  --ignore=venv
translate:
	django-admin compilemessages --ignore=static --ignore=media  --ignore=venv
test_data_discounts:
	python market_place_proj/manage.py discounts
test_data_cart_sale:
	python market_place_proj/manage.py cart_sale
pay:
	python market_place_proj/manage.py rabbit