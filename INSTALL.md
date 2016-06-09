+------------------------+
- PoliCrowd		 -
+------------------------+

- NO se puede instalar Vagrant en el servidor porque no se puede correr VirtualBox con KVM corriendo en el servidor.
  Instalacion hecha SIN usar Vagrant:

https://github.com/YoQuieroSaber/yournextrepresentative/wiki/Production-Deploy




Production Deploy

https://github.com/YoQuieroSaber/yournextrepresentative.wiki.git

If you're not using vagrant in production and you need to get all the pre-requisites installed for YourNextMP in a newly configured VPS, these are the commands you should run:

Environment installation

sudo apt-get update

sudo apt-get install git python-pip postgresql-server-dev-all postgresql libffi-dev python-dev libffi-dev libssl-dev libxml2-dev libxslt1-dev ruby libjpeg-dev

sudo gem install sass -v 3.4.21


Configure PostgreSQL

	change to root user and edit hba file

	~$ su -
	~$ vim /etc/postgresql/9.3/main/pg_hba.conf

	add te next line

		# TYPE  DATABASE        USER            ADDRESS                 METHOD
		local   all             ynr                                     md5

	reload to postgress configuration

	~$ /etc/init.d/postgresql reload

	change to postgres user

	~$ su - postgres

	create database and user

	~$ createdb ynr
	~$ psql
	CREATE USER ynr WITH PASSWORD 'vivalavida';


Virtualenv instalation:

	http://hosseinkaz.blogspot.com.ar/2012/06/how-to-install-virtualenv.html

mkvirtualenv poli

git clone --recursive https://github.com/conocimientoabierto/policrowd.git

Copy the example configuration file to conf/general.yml:

	cp conf/general.yml-example conf/general.yml

Edit conf/general.yml to fill in details of the PopIt instance you're using.

	- Change:
	ELECTION_APP: 'ar_policrowd_2016'
	LANGUAGE_CODE: 'es-ar'

	YNMP_DB_USER: 'ynr'
	YNMP_DB_NAME: 'ynr'
	YNMP_DB_PASS: 'vivalavida'
	YNMP_DB_PORT: ''
	YNMP_DB_HOST: 'localhost'

	 - ADD:
   DEFAULT_AREA: 'Argentina' #This should match the country in the imported areas

cd yournextrepresentative

pip install -r requirements.txt


python manage.py migrate

python manage.py createsuperuser

# Make sure elastichsearch is running. You might need to decrease heap size.
sudo /usr/share/elasticsearch/bin/elasticsearch -d

./manage.py ar_policrowd_import_areas
./manage.py ar_policrowd_import_politicians

# Compile language files
./manage.py compilemessages

Run the ynr server
./manage.py runserver

Access: http://localhost:8000



Para correrlo en ocasiones posteriores, correr:

workon poli

./manage.py runserver 0.0.0.0:8000
