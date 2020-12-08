from infomentor import model
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from infomentor import config
_session = None

conf = config.load()

def get_db(filename="infomentor.db"):
    """Get the database session for infomentor"""
    global _session
    if _session is None:
        connect_string = conf['db']['type']+'://postgres:'+conf['db']['password']+'@'+conf['db']['server']+'/'+conf['db']['database']
        engine = create_engine(connect_string)
        model.ModelBase.metadata.create_all(engine)
        model.ModelBase.metadata.bind = engine
        DBSession = sessionmaker(bind=engine)
        _session = DBSession()
    return _session
