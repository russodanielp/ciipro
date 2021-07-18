from ciipro.routes import db
from werkzeug.security import generate_password_hash, check_password_hash
# TODO: remove this into its own module
# I was having issues with circular
# imports


from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

import pandas as pd
from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D

from sqlalchemy import Column, Integer, String, Float
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


class Dataset(db.Model):
    """ main table to hold a users' datasets """
    __tablename__ = 'datasets'
    id = db.Column('id', db.Integer, primary_key=True)
    activity_description = db.Column('float', db.Float)
    owner_id = db.Column('owner_id', db.Integer, db.ForeignKey("users.user_id"))

    # chemicals = relationship("Chemical", back_populates="dataset")
    chemicals = db.relationship("Chemical", backref='datasets', uselist=True)
    #owner = relationship("User", back_populates="datasets")

class Chemical(db.Model):
    """ users chemical class.  Every uploaded chemical for a user should have
     at least three properties, an activity, inchi, and canonical smiles.  """
    __tablename__ = 'chemicals'
    id = db.Column('id', db.Integer, primary_key=True)
    activity = db.Column('activity', db.Float)
    inchi = db.Column('inchi', db.String)
    smiles = db.Column('smiles', db.String)

    dataset_id = db.Column('dataset_id', db.Integer, db.ForeignKey("datasets.id"))
    dataset = relationship("Dataset", back_populates='chemicals')


db.create_all()
