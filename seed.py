import models
from database import engine

# Create all tables described by the models.
# If the users table does not exist yet, this line creates it.
models.Base.metadata.create_all(bind=engine)

print("Piazza database tables created.")
