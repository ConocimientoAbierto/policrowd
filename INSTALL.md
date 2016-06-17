# Installing PoliCrowd

If you are not installing on a virtual server, the easiest path is the vagrant installating described here, but this cannot be done on virtual servers.

https://github.com/YoQuieroSaber/yournextrepresentative/wiki/Production-Deploy


If you're not using vagrant in production and you need to get all the pre-requisites installed for YourNextMP in a newly configured VPS, these are the commands you should run:

## Environment installation

```
sudo apt-get update

sudo apt-get install git python-pip postgresql-server-dev-all postgresql libffi-dev python-dev libffi-dev libssl-dev libxml2-dev libxslt1-dev ruby libjpeg-dev elasticsearch

sudo gem install sass -v 3.4.21
```


## Configure PostgreSQL

PostgreSQL needs to allow md5 logins for our user.

As root user and edit hba file

```
sudo nano /etc/postgresql/9.3/main/pg_hba.conf 
```

(you can use vi or your prefered editor instead of nano here)

Add the following line at the end of pg_hba.conf

    TYPE  DATABASE        USER            ADDRESS                 METHOD
    local   all             ynr                                     md5

Reload to postgress configuration

```
/etc/init.d/postgresql reload
```

Switch to postgres user

```
sudo su - postgres
```

Create database and user

```
createdb ynr
psql
```
Inside psql write

```
CREATE USER ynr WITH PASSWORD 'vivalavida';
```

Note: Please change your password.

## Set up the python environment

Virtualenv instalation:

Follow the instructions here: http://hosseinkaz.blogspot.com.ar/2012/06/how-to-install-virtualenv.html

```
mkvirtualenv poli
git clone --recursive https://github.com/conocimientoabierto/policrowd.git
```

## Configure the app

Copy the example configuration file to conf/general.yml:

```
cp conf/general.yml-example conf/general.yml
```

Edit conf/general.yml to fill in details of the PopIt instance you're using.

```
#CHANGE THE FOLLOWING VALUES:
ELECTION_APP: 'ar_policrowd_2016'
LANGUAGE_CODE: 'es-ar'

YNMP_DB_USER: 'ynr'
YNMP_DB_NAME: 'ynr'
YNMP_DB_PASS: 'vivalavida'
YNMP_DB_PORT: ''
YNMP_DB_HOST: 'localhost'

#ADD THIS LINE:
DEFAULT_AREA: 'Argentina'
```

### Install python requirements and configure the application

```
cd policrowd
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

At this point please *make sure elasticsearch is running*. You might need to decrease heap size or force it to run with:
```
sudo /usr/share/elasticsearch/bin/elasticsearch -d
```

## Import initial data

```
./manage.py ar_policrowd_import_areas
./manage.py ar_policrowd_import_politicians
```

Compile language files
```
./manage.py compilemessages
```

# Run the policrowd server
```
./manage.py runserver
```

At this point you should be able to access the app at: http://localhost:8000


For subsequent runs, just use

```
workon poli
./manage.py runserver 0.0.0.0:8000
```

If the log-in page shows an ImproperlyConfigured error, then you need to add a SocialApp in the adming, go to: http://127.0.0.1:8000/admin/socialaccount/socialapp/add/

You will need to create a facebook app and configure it. Please refer to facebook's documentation.
