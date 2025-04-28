from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
import uvicorn
from typing import List
from pydantic import BaseModel, ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

app = FastAPI()

# Конфигурация JWT
SECRET_KEY = "mysecret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

users = {"admin": {"password": "secret"}}
messages = []

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

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
    message_id: int

class MessageDelete(BaseModel):
    message_id: int

class MessageResponse(BaseModel):
    id: int
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

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None or username not in users:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"username": username}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Эндпоинт для логина (получение токена)
@app.post("/login", response_model=TokenResponse)
def login(form_data: UserCreate):
    user = users.get(form_data.username)
    if not user or user["password"] != form_data.password:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return TokenResponse(access_token=create_token(form_data.username), token_type="bearer")

# Эндпоинт для создания нового пользователя
@app.post("/users/", response_model=UserCreateResponse)
def create_user(user: UserCreate):
    if user.username in users:
        raise HTTPException(status_code=400, detail="User already exists")
    users[user.username] = {"password": user.password}
    return UserCreateResponse(message=f"User {user.username} created")

# Эндпоинт для удаления пользователя
@app.delete("/users/{username}", response_model=UserDeleteResponse)
def delete_user(username: str, user: UserDelete, current_user: dict = Depends(get_current_user)):
    if user.username not in users:
        raise HTTPException(status_code=404, detail="User not found")
    if user.username != current_user["username"] and current_user["username"] != "admin":
        raise HTTPException(status_code=403, detail="You can only delete your own account")
    del users[user.username]
    return UserDeleteResponse(message=f"User {user.username} deleted")

# Эндпоинт для получения информации о себе (нужен токен)
@app.get("/users/{username}", response_model=UserResponse)
def read_users_me(username: str):
    if username in users:
        return UserResponse(username=username)
    else:
        raise HTTPException(status_code=404, detail="User not found")

# Эндпоинт для отправки сообщения
@app.post("/users/{username}/messages/", response_model=MessageCreateResponse)
def send_message(username:str, msg: MessageCreate, current_user: dict = Depends(get_current_user)):
    if not (current_user["username"] == username or current_user["username"] == "admin"):
        raise HTTPException(status_code=403, detail='access denied')
    if username not in users:
        raise HTTPException(status_code=404, detail="Sender not found")
    if msg.recipient not in users:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    message_id = len(messages) + 1
    messages.append({
        "id": message_id,
        "sender": username,
        "recipient": msg.recipient,
        "text": msg.text,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    return MessageCreateResponse(message="Message sent", message_id=message_id)

# Эндпоинт для получения всех своих сообщений
@app.get("/users/{username}/messages/", response_model=MessagesResponse)
def get_messages(username:str, current_user: dict = Depends(get_current_user)):
    if not (current_user["username"] == username or current_user["username"] == "admin"):
        raise HTTPException(status_code=403, detail='access denied')
    if username not in users:
        raise HTTPException(status_code=404, detail="User not found")

    user_messages = [
        MessageResponse(msg["id"], msg["sender"], msg["recipient"], msg["text"])  
        for msg in messages if msg["recipient"] == current_user["username"]
    ]

    return MessagesResponse(messages=user_messages) 

# Эндпоинт для удаления сообщения
@app.delete("/users/{username}/messages/", response_model=MessageDeleteResponse)
def delete_message(username:str, msg: MessageDelete, current_user: dict = Depends(get_current_user)):
    if not (current_user["username"] == username or current_user["username"] == "admin"):
        raise HTTPException(status_code=403, detail='access denied')
    if username not in users:
        raise HTTPException(status_code=404, detail="User not found")
    for i, message in enumerate(messages):
        if message["id"] == msg.message_id:
            if message["sender"] != username:
                raise HTTPException(status_code=403, detail="You can only delete your own messages")
            del messages[i]
            return MessageDeleteResponse(message="Message deleted")
    
    raise HTTPException(status_code=404, detail="Message not found")


if __name__ == "__main__":
    uvicorn.run(app, host="app", port=8080)