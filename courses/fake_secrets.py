# MySQL connection stuff
#DB_CONNECTION = {
#    'NAME': '',
#    'USER': '',
#    'PASSWORD': '',
#    'HOST': '',
#    'PORT': 4000,
#}

# 50-random-character secret key for crypto thingies. Use tools/secret_key_gen.py to create a good one if needed
SECRET_KEY = 'THIS IS NOT A VERY SECRET KEY'

# passwords for various connections:
SVN_DB_PASS = ''
AMPQ_PASSWORD = 'supersecretpassword'
EMPLID_API_SECRET = ''
INITIAL_PHOTO_PASSWORD = '' # will be injected into database by 'manage.py install_secrets', if needed

# reporting DB connection
SIMS_USER = 'ggbaker'
SIMS_PASSWORD = ''

#BACKUP_REMOTE_URL = 'scp://userid@backups.cs.sfu.ca//backups/coursys'
#BACKUP_KEY_ID = 'coursys-help@sfu.ca'
#BACKUP_KEY_PASSPHRASE = 'abc123'