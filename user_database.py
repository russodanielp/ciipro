from ciipro.routes import db
#from routes import app
from werkzeug.security import generate_password_hash, check_password_hash
# Refer: https://docs.sqlalchemy.org/en/14/orm/basic_relationships.html


from sqlalchemy import ForeignKey
from sqlalchemy import and_, or_
from sqlalchemy.orm import relationship

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import func

import pandas as pd
from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D

from sqlalchemy import Column, Integer, String, Float, Table
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class User(db.Model):
    """ sqlalchemly model for handling login information """
    __tablename__ = "users"
    id = db.Column('user_id', db.Integer, primary_key=True)
    username = db.Column('username', db.String(20), unique=True, index=True)
    pw_hash = db.Column('password', db.String(10))
    email = db.Column('email', db.String(50), unique=True, index=True)

    # datasets_id = db.Column('datasets_id', db.String, db.ForeignKey("datasets.id"))
    datasets = db.relationship("Dataset", backref='users', uselist=True)

    def __init__(self, username, password, email):
        self.username = username
        self.set_password(password)
        self.email = email

    def set_password(self, password):
        """ generates and stores a password hash for a given users password. using
        werkzeug's generate_pa"""
        self.pw_hash = generate_password_hash(password, method='pbkdf2:sha1',
                                              salt_length=8)

    def check_password(self, password):
        """ checks a users password against the hash from we """
        return check_password_hash(self.pw_hash, password)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return '<User %r>' % (self.username)

    def add_user_dataset(self, name: str, data: pd.DataFrame):
        """ adds a dataset to a user by adding a dataset to the datasets table and
        all the chemicals in the chemicals table

        data: a pandas dataframe in the ciipro containing columns for smiles, inchi, activity,
        and cid
        """
        chemicals = []
        dataset = Dataset(name=name, owner_id=self.id)
        db.session.add(dataset)
        db.session.commit()

        for i, row in data.iterrows():
            chemical = db.session.query(Chemical).filter_by(id=row.cid).first()

            if not chemical:
                chemical = Chemical(id=row.cid,
                                    smiles=row.smiles,
                                    inchi=row.inchi)

            activity = Activity(value=row.activity,
                                dataset_id=dataset.id,
                                chemical_id=chemical.id)
            chemical.activities.append(activity)
            chemicals.append(chemical)
            #dataset.chemicals.append(activity)


        db.session.add(dataset)
        db.session.add_all(chemicals)
        db.session.commit()

    def get_user_dataset_names(self):
        return [ds.name for ds in self.datasets]

    def get_user_dataset(self, name):
        dataset = db.session.query(Dataset) \
                    .join(Dataset, User.datasets) \
                    .filter(Dataset.name == name).first()
        return dataset

    def dataset_name_exists(self, name):
        return db.session.query(Dataset) \
                    .filter(Dataset.name == name).first()

# an association table is needed for chemicals
# and datasets because they are a Many-to-Many
# relationship


class Activity(db.Model):
    __tablename__ = 'activities'
    id = Column('id', db.Integer, primary_key=True)
    chemical_id = Column(ForeignKey('chemicals.id'))
    dataset_id = Column(ForeignKey('datasets.id'))
    chemical = relationship("Chemical", back_populates="activities")
    dataset = relationship("Dataset", back_populates="chemicals")

    value = Column('value', db.Float)
    units = Column('units', db.String)

class Dataset(db.Model):
    """ main table to hold a users' datasets """
    __tablename__ = 'datasets'
    id = db.Column('id', db.Integer, primary_key=True)
    name = db.Column('String', db.String, unique=True)
    owner_id = db.Column('owner_id', db.Integer, db.ForeignKey("users.user_id"))

    # chemicals = relationship("Chemical", back_populates="dataset")
    chemicals = db.relationship("Activity", back_populates='dataset')
    #owner = relationship("User", back_populates="datasets")

    def __init__(self, name, owner_id):
        self.owner_id = owner_id
        self.name = name

    def get_activities(self):
        return [activity.value for activity in self.chemicals]

    def get_num_chemicals(self):
        return len(self.chemicals)

    def get_chemicals(self):
        """ get chemicals associated with this dataset """
        query = db.session.query(Dataset) \
                        .filter(Dataset.id == self.id) \
                        .join(Activity, Dataset.id == Activity.dataset_id) \
                        .join(Chemical, Activity.chemical_id == Chemical.id) \
                        .with_entities(Chemical.inchi, Activity.value, Chemical.id)
        return pd.read_sql(query.statement, query.session.bind)

class Chemical(db.Model):
    """ users chemical class.  Every uploaded chemical for a user should have
     at least three properties, an activity, inchi, and canonical smiles.  """
    __tablename__ = 'chemicals'
    id = db.Column('id', db.Integer, primary_key=True)
    inchi = db.Column('inchi', db.String)
    smiles = db.Column('smiles', db.String)

    #dataset_id = db.Column('dataset_id', db.Integer, db.ForeignKey("datasets.id"))
    #datasets = db.relationship("Association", back_populates='chemical')
    activities = db.relationship("Activity", backref='chemicals', uselist=True)

# class Activity(db.Model):
#     """ activity class.  an activity should belone to one chemical and one dataset """
#     __tablename__ = 'activities'
#     id = db.Column('id', db.Integer, primary_key=True)
#     activity = db.Column('activity', db.Float)
#
#
#     dataset_id = db.Column('dataset_id', db.Integer, db.ForeignKey("datasets.id"))
#     chemical_id = db.Column('chemical_id', db.Integer, db.ForeignKey("chemicals.id"))

db.create_all()

if __name__ == '__main__':
    data = db.session.query(Dataset).filter(Dataset.name == 'BBB')
    print(data)




