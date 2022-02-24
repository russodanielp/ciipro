from ciipro.routes import db
from werkzeug.security import generate_password_hash, check_password_hash
# Refer: https://docs.sqlalchemy.org/en/14/orm/basic_relationships.html


from sqlalchemy import ForeignKey
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

        dataset = Dataset(name=name, owner_id=self.id)
        db.session.add(dataset)
        db.session.commit()

        for i, row in data.iterrows():
            chemical = db.session.query(Chemical).filter_by(id=row.cid).first()

            if not chemical:
                chemical = Chemical(id=row.cid,
                                    smiles=row.smiles,
                                    inchi=row.inchi,
                                    dataset_id=dataset.id)

            activity = Activity(activity=row.activity,
                                dataset_id=dataset.id,
                                chemical_id=chemical.id)
            chemical.activities.append(activity)
            a = Association()
            a.chemical = chemical
            dataset.chemicals.append(a)


        db.session.add(dataset)
        db.session.commit()

    def get_user_datasets(self):
        return self.datasets


# an association table is needed for chemicals
# and datasets because they are a Many-to-Many
# relationship


class Association(db.Model):
    __tablename__ = 'association'
    chemical_id = Column(ForeignKey('chemicals.id'), primary_key=True)
    dataset_id = Column(ForeignKey('datasets.id'), primary_key=True)
    chemical = relationship("Chemical", back_populates="datasets")
    dataset = relationship("Dataset", back_populates="chemicals")

class Dataset(db.Model):
    """ main table to hold a users' datasets """
    __tablename__ = 'datasets'
    id = db.Column('id', db.Integer, primary_key=True)
    name = db.Column('String', db.String)
    owner_id = db.Column('owner_id', db.Integer, db.ForeignKey("users.user_id"))

    # chemicals = relationship("Chemical", back_populates="dataset")
    chemicals = db.relationship("Association", back_populates='dataset')
    #owner = relationship("User", back_populates="datasets")


class Chemical(db.Model):
    """ users chemical class.  Every uploaded chemical for a user should have
     at least three properties, an activity, inchi, and canonical smiles.  """
    __tablename__ = 'chemicals'
    id = db.Column('id', db.Integer, primary_key=True)
    inchi = db.Column('inchi', db.String)
    smiles = db.Column('smiles', db.String)

    dataset_id = db.Column('dataset_id', db.Integer, db.ForeignKey("datasets.id"))
    datasets = db.relationship("Association", back_populates='chemical')
    activities = db.relationship("Activity", backref='chemicals', uselist=True)

class Activity(db.Model):
    """ activity class.  an activity should belone to one chemical and one dataset """
    __tablename__ = 'activities'
    id = db.Column('id', db.Integer, primary_key=True)
    activity = db.Column('activity', db.Float)


    dataset_id = db.Column('dataset_id', db.Integer, db.ForeignKey("datasets.id"))
    chemical_id = db.Column('chemical_id', db.Integer, db.ForeignKey("chemicals.id"))

db.create_all()






