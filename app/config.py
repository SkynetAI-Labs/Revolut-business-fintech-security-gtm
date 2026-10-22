import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
JWT_ALGORITHM = os.environ["JWT_ALGORITHM"]
JWT_EXPIRE_MINUTES = int(os.environ["JWT_EXPIRE_MINUTES"])
