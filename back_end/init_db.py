from w101.database import Base, engine
from w101.models import *

print("Creating tables...")
Base.metadata.create_all(engine)
print("Done.")