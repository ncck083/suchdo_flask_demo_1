# database-config
USERNAME = 'root'
PASSWORD = '1234'
HOST = '127.0.0.1'
PORT = '3306'
DATABASE = 'suchdo'

SQLALCHEMY_DATABASE_URI = "mysql://{}:{}@{}:{}/{}?charset=utf8".format(USERNAME, PASSWORD, HOST, PORT, DATABASE)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# file-upload config
UPLOAD_FOLDER = 'upload_dir'
MAX_CONTENT_PATH = '1000000000'
