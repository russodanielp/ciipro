from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base

import pandas as pd
from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D

from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker


Base = declarative_base()

engine = create_engine('sqlite:///.app.db', echo=True)

Session = sessionmaker(bind=engine)

class Dataset(Base):
    """ main table to hold a users' datasets """
    __tablename__ = 'datasets'
    id = Column(String, primary_key=True)
    activity_description = Column(String)
    chemicals = relationship("Chemical", back_populates="dataset")

class Chemical(Base):
    """ users chemical class.  Every uploaded chemical for a user should have
     at least three properties, an activity, inchi, and canonical smiles.  """
    __tablename__ = 'chemicals'
    id = Column(Integer, primary_key=True)
    activity = Column(Float)
    inchi = Column(String)
    smiles = Column(String)
    dataset_id = Column(String, ForeignKey("datasets.id"))

    dataset = relationship("Dataset", back_populates='chemicals')
