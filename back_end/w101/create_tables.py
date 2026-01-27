from w101.database import Base, engine
import w101.models  # IMPORTANT: ensures models register with Base

Base.metadata.create_all(bind=engine)
print("Tables created.")