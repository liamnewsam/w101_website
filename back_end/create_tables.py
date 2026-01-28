from database import Base, engine
import models  # IMPORTANT: ensures models register with Base

Base.metadata.create_all(bind=engine)
print("Tables created.")