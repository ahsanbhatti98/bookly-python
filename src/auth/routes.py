from fastapi import APIRouter, Depends, status
from .schemas import (
    UserCreateModel,
    UserModel,
    UserLoginModel,
    UserBooksModel,
    EmailModel,
)
from .service import UserService
from src.db.main import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from .utils import (
    create_access_token,
    decode_token,
    verify_password,
    create_url_safe_token,
    decode_url_safe_token,
)
from datetime import timedelta, datetime
from src.config import Config
from .dependencies import (
    RefreshTokenBearer,
    AccessTokenBearer,
    get_current_user,
    RoleChecker,
    InvalidToken,
)
from src.db.redis import add_token_to_blocklist
from src.errors import UserAlreadyExists, UserNotFound, InvalidCredentials
from src.mail import create_message, mail
from src.config import Config

auth_router = APIRouter()
user_service = UserService()
refresh_token_bearer = RefreshTokenBearer()
access_token_bearer = AccessTokenBearer()
role_checker = RoleChecker(["admin", "user"])


@auth_router.post("/send_mail")
async def send_email(emails: EmailModel):
    emails = emails.addresses

    html = "<h1>Welcome to Bookly APP</h1>"

    message = create_message(
        recipient=emails,
        subject="Welcome",
        body=html,
    )

    await mail.send_message(message)

    return {"message": "Email sent successfully!"}


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def create_user_account(
    user_data: UserCreateModel, session: AsyncSession = Depends(get_session)
):
    email = user_data.email

    user_exists = await user_service.user_exists(email, session)

    if user_exists:
        raise UserAlreadyExists()

    new_user = await user_service.create_user(user_data, session)

    token = create_url_safe_token({"email": email})
    link = f"http:{Config.DOMAIN_NAME}/api/v1/auth/verify/{token}"

    html_message = f"""
    <h1>Welcome to Bookly APP</h1>
    <p>Hi {user_data.first_name} {user_data.last_name},</p>
    <p>Please verify your email address by clicking the link below:</p>
    <a href="{link}">Verify Email</a>
    """

    message = create_message(
        recipient=[email],
        subject="Welcome",
        body=html_message,
    )

    await mail.send_message(message)

    return {
        "message": "Account created! check your email to verify your account",
        "user": new_user,
    }


@auth_router.get("/verify/{token}")
async def verify_email(token: str, session: AsyncSession = Depends(get_session)):
    token_data = decode_url_safe_token(token)
    user_email = token_data.get("email")

    if user_email:
        user = await user_service.get_user_by_email(user_email, session)
        if not user:
            raise UserNotFound()

        await user_service.update_user(user, {"is_verified": True}, session)
        return JSONResponse(
            content={"message": "Email verified successfully"},
            status_code=status.HTTP_200_OK,
        )

    return JSONResponse(
        content={"message": "Error occurred during email verification"},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@auth_router.post("/login")
async def login(
    login_data: UserLoginModel, session: AsyncSession = Depends(get_session)
):
    email = login_data.email
    password = login_data.password

    user = await user_service.get_user_by_email(email, session)

    if user is not None:
        password_valid = verify_password(password, user.password_hash)

        if password_valid:
            access_token = create_access_token(
                user_data={
                    "email": user.email,
                    "user_uid": str(user.uid),
                    "role": user.role,
                }
            )

            refresh_token = create_access_token(
                user_data={"email": user.email, "user_uid": str(user.uid)},
                expiry=timedelta(days=Config.REFRESH_TOKEN_EXPIRE_DAYS),
                refresh=True,
            )

            return JSONResponse(
                content={
                    "message": "Login successful",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }
            )

        else:
            raise InvalidCredentials()
    else:
        raise UserNotFound()


@auth_router.post("/refresh_token")
async def get_new_access_token(token_details: dict = Depends(refresh_token_bearer)):
    expiry_timestamp = token_details["exp"]

    if datetime.fromtimestamp(expiry_timestamp) > datetime.now():
        new_access_token = create_access_token(user_data=token_details["user"])

        return JSONResponse(content={"access_token": new_access_token})

    raise InvalidToken()


@auth_router.get("/me", response_model=UserBooksModel)
async def get_currrent_user(
    user=Depends(get_current_user), _: bool = Depends(role_checker)
):
    return user


@auth_router.get("/logout")
async def revoke_token(token_details: dict = Depends(access_token_bearer)):

    jti = token_details["jti"]

    await add_token_to_blocklist(jti)

    return JSONResponse(
        content={"message": "Logout successful"}, status_code=status.HTTP_200_OK
    )
