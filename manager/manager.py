"""

Module that instantiates flask-script manager for running stand-alone scripts on the app

Ref link: https://flask-script.readthedocs.io/en/latest/

"""

from routes import app, User
from flask_script import Manager

manager = Manager(app)

@manager.command
def get_db_users():
    users = User.query.all()
    print("\n".join(map(str, users)))


if __name__ == "__main__":
    manager.run()

