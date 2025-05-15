from passlib.context import CryptContext
from datetime import datetime, timedelta
from src.config import Config
import jwt
import uuid
import logging

password_context = CryptContext(
    schemes=["bcrypt"],
)


def get_password_hash(password: str) -> str:
    hash = password_context.hash(password)

    return hash


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def create_access_token(
    user_data: dict, expiry: timedelta = None, refresh: bool = False
):
    payload = {}

    payload["user"] = user_data
    payload["exp"] = datetime.utcnow() + (
        expiry
        if expiry is not None
        else timedelta(seconds=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload["jti"] = str(uuid.uuid4())

    payload["refresh"] = refresh

    token = jwt.encode(
        payload=payload, key=Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM
    )

    return token


def decode_token(token: str) -> dict:
    try:
        token_data = jwt.decode(
            jwt=token, key=Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM]
        )

        return token_data

    except jwt.PyJWTError as e:
        logging.exception(e)
        return None
