# Digital Twin Platform

## Requirements
In order to install packages that help to render the user interface, run:
```bash
sudo apt install npm, libpq-dev
npm install popper.js
npm install jquery
npm install bootstrap 
```

**postgres** must be up and running on the default port `5432` and the database `iot4cps`.
In order to change the database, the database name, or the database driver, manipulate the
SQLALCHEMY_DATABASE_URI in the proper mode files in `server/config`: 

```python
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://iot4cps:iot4cps@localhost/iot4cps'  
```


## Create the (initial) database

This command will fill the database with sample instances that are 
described in the demonstration use case.

```bash
cd /panta_rhei
virtualenv --python=/path/to/base/python .venv
source .venv/bin/python activate
pip install -r requirements.txt
python server/create_database.py
```

Check if everything works by running:
```bash
sudo -u postgres psql -d iot4cps -c "SELECT * FROM users;"
```

## Start the platform

Make sure that the file `server/.env` directs to the correct configuration set, that is 
either `development`, `production` or `platform-only` (that doesn't interact with the
Kafka data streaming).
The platform can be started by running:
```bash
export FLASK_APP=$(pwd)/server/app.py
echo $FLASK_APP
source /path/to/venv/bin/activate
python -m flask run --host $(hostname -I) --port 1908
```

Now, the service is available on [localhost:1908](localhost:1908).

To allow external access, don't forget to open the 
firewall on this port `sudo ufw allow 1908/tcp`.
