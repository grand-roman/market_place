sudo useradd django -p Django2021 -G www-data
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install -y mc
sudo apt-get install -y python3-pip
sudo apt-get install -y python3-venv
sudo apt-get install -y redis-server
sudo apt-get install -y postgresql
sudo apt-get install -y curl gnupg
curl -1sLf "https://keys.openpgp.org/vks/v1/by-fingerprint/0A9AF2115F4687BD29803A206B73A36E6026DFCA" | sudo gpg --dearmor | sudo tee /usr/share/keyrings/com.rabbitmq.team.gpg > /dev/null
curl -1sLf https://dl.cloudsmith.io/public/rabbitmq/rabbitmq-erlang/gpg.E495BB49CC4BBE5B.key | sudo gpg --dearmor | sudo tee /usr/share/keyrings/io.cloudsmith.rabbitmq.E495BB49CC4BBE5B.gpg > /dev/null
curl -1sLf https://dl.cloudsmith.io/public/rabbitmq/rabbitmq-server/gpg.9F4587F226208342.key | sudo gpg --dearmor | sudo tee /usr/share/keyrings/io.cloudsmith.rabbitmq.9F4587F226208342.gpg > /dev/null
sudo apt-get install apt-transport-https
#rabbitmq.list
sudo cp rabbitmq.list /etc/apt/sources.list.d
sudo apt-get update -y
sudo apt install -y erlang-base \
erlang-asn1 erlang-crypto erlang-eldap erlang-ftp erlang-inets \
erlang-mnesia erlang-os-mon erlang-parsetools erlang-public-key \
erlang-runtime-tools erlang-snmp erlang-ssl \
erlang-syntax-tools erlang-tftp erlang-tools erlang-xmerl
sudo apt-get install rabbitmq-server -y --fix-missing
sudo systemctl enable rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management
sudo rabbitmqctl add_user admin Django2021
sudo rabbitmqctl set_user_tags admin administrator
sudo rabbitmqctl set_permissions -p / admin ".*" ".*" ".*"
sudo apt-get install -y git
sudo apt-get install -y memcached libmemcached-tools
sudo systemctl restart memcached
sudo apt-get install -y nginx
sudo su -c "psql -c \"CREATE USER django WITH PASSWORD 'Django2021'\"" postgres
sudo su - postgres -c "createdb megano;"
sudo su -c "psql -c \"grant all privileges on database megano to django\"" postgres

python3 -m pip install --upgrade pip
mkdir /py && cd /py
python3 -m venv /py/venv
source /py/venv/bin/activate
git clone https://gitlab.skillbox.ru/learning_materials/python_django_group_diploma.git
sudo sudo chown django -r /py
sudo sudo chmod 775 -r /pi
sudo sudo chmod ugo+x market_place_proj/install/*.sh
cd python_django_group_diploma/
sudo cp market_place_proj/install/megano /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/megano /etc/nginx/sites-enabled
sudo cp market_place_proj/install/gunicorn.socket /etc/systemd/system
sudo cp market_place_proj/install/gunicorn.socket /etc/systemd/system
pip install -r requirements.txt
make migrate
make test_data
sudo systemctl start gunicorn.socket
sudo systemctl enable gunicorn.socket
sudo apt-get install -y python3-certbot-nginx
sudo systemctl restart nginx