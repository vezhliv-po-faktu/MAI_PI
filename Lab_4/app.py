from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
import uvicorn
from typing import List
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from passlib.context import CryptContext
import os

from bson import ObjectId
from mongodb import messages_collection

from models import User 
# http://localhost:8080/docs


# контекст для хэширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# хэширование пароля
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, password: str) -> bool:
    return pwd_context.verify(plain_password, password)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@postgres:5432/social_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class MyModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

app = FastAPI()

# JWT
SECRET_KEY = "mysecret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

auth_scheme = HTTPBearer()

class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    username: str

class UserDelete(BaseModel):
    username: str

class UserCreateResponse(BaseModel):
    message: str

class UserDeleteResponse(BaseModel):
    message: str

class MessageCreate(BaseModel):
    recipient: str
    text: str

class MessageCreateResponse(BaseModel):
    message: str

class MessageDelete(BaseModel):
    message_id: int

class MessageResponse(BaseModel):
    id: str
    sender: str
    recipient:str
    text: str

class MessagesResponse(BaseModel):
    messages: List[MessageResponse]

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class MessageDeleteResponse(BaseModel):
    message: str


def create_token(username: str):
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    data = {"sub": username, "exp": expire}
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: HTTPAuthorizationCredentials = Depends(auth_scheme), db: Session = Depends(get_db)):
    try:
        token = token.credentials

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = db.query(User).filter_by(username=username).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Эндпоинт для логина (получение токена)
@app.post("/login", response_model=TokenResponse)
def login(form_data: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    token = create_token(user.username)
    return TokenResponse(access_token=token, token_type="bearer")


# Эндпоинт для создания нового пользователя
@app.post("/users/", response_model=UserCreateResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter_by(username=user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    password = hash_password(user.password)
    db_user = User(username=user.username, password=password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return UserCreateResponse(message=f"User {db_user.username} created")


# Эндпоинт для удаления пользователя
@app.delete("/users/{username}", response_model=UserDeleteResponse)
def delete_user(username: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter_by(username=username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if username != current_user.username and current_user.username != "admin":
        raise HTTPException(status_code=403, detail="You can only delete your own account or be an admin")

    db.delete(user)
    db.commit()
    
    return UserDeleteResponse(message=f"User {username} deleted")


# Эндпоинт для получения информации о себе (нужен токен)
@app.get("/users/me", response_model=UserResponse)
def get_user_info(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=current_user.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(username=user.username)


# Эндпоинт для отправки сообщения
@app.post("/users/{username}/messages/", response_model=MessageCreateResponse)
async def send_message(
    username: str,
    msg: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if username != current_user.username and current_user.username != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    recipient_user = db.query(User).filter_by(username=msg.recipient).first()
    if not recipient_user:
        raise HTTPException(status_code=404, detail="Recipient not found")

    message = {
        "sender": current_user.username,
        "recipient": msg.recipient,
        "text": msg.text,
        "timestamp": datetime.utcnow()
    }
    result = await messages_collection.insert_one(message)

    return MessageCreateResponse(message="Message sent")


# Эндпоинт для получения всех своих сообщений
@app.get("/users/{username}/messages/", response_model=MessagesResponse)
async def get_messages(username: str, current_user: User = Depends(get_current_user)):
    if current_user.username != username and current_user.username != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    messages_cursor = messages_collection.find({"recipient": username})
    messages = await messages_cursor.to_list(length=100)

    if not messages:
        raise HTTPException(status_code=404, detail="No messages found")

    return MessagesResponse(messages=[
        MessageResponse(
            id = str(msg["_id"]),
            sender=msg["sender"],
            recipient=msg["recipient"],
            text=msg["text"]
        ) for msg in messages
    ])


# Эндпоинт для удаления сообщения
@app.delete("/users/{username}/messages/{message_id}", response_model=MessageDeleteResponse)
async def delete_message(username: str, message_id: str, current_user: User = Depends(get_current_user)):
    message = await messages_collection.find_one({"_id": ObjectId(message_id)})

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if message["sender"] != current_user.username and current_user.username != "admin":
        raise HTTPException(status_code=403, detail="You can only delete your own messages")

    await messages_collection.delete_one({"_id": ObjectId(message_id)})
    return MessageDeleteResponse(message="Message deleted")


if __name__ == "__main__":
    uvicorn.run(app, host="app", port=8080)