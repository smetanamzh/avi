from app.database.database import Base, engine
import app.database.models

Base.metadata.create_all(engine)

print("Database created!")