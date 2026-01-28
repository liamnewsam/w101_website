from database import Base, engine
from models import *

print("Creating tables...")
Base.metadata.create_all(engine)
print("Done.")