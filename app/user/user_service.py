from fastapi import Request
from app.user.user_model import User
from app.common.api import success_response
from app.user.user_model import UserCreateRequest, UserUpdateRequest, UserSignInRequest
from app.common.exception import duplicated_email, password_rule_violation, sign_in_data_not_match, invalid_jwt, \
    expired_jwt, undefined_error, jwt_data_not_match, not_found
from app.common.jwt import create_tokens, decode_token, create_access_token
import bcrypt
import re


# 사용자 생성
def create_user(db_session, user: UserCreateRequest):
    # 이메일 중복 체크
    if email_check(db_session, user.email):
        return duplicated_email()
    # 비밀번호 규칙 체크
    if not bool(re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*()-+=]).{8,}$", user.password)):
        return password_rule_violation()

    salt = bcrypt.gensalt()
    db_user = User(username=user.username, email=user.email, password=bcrypt.hashpw(user.password.encode('utf-8'), salt),
                   salt=salt)
    db_session.add(db_user)
    db_session.commit()
    db_session.refresh(db_user)
    return success_response(db_user.to_dict())


# 이메일 중복 검사
def email_check(db_session, email: str):
    user = db_session.query(User).filter(User.email == email).first()
    if user is not None:
        return True
    else:
        return False


# 사용자 조회
def get_user(db_session, user: UserSignInRequest):
    data = db_session.query(User).filter(User.email == user.email).first()
    if data is not None:
        if user.password == bcrypt.hashpw(user.password.encode('utf-8'), data.salt):
            token = create_tokens(data.to_dict())
            return success_response(
                {
                    "access_token": token["access"],
                    "refresh_token": token["refresh"]
                }
            )
        else:
            return sign_in_data_not_match()
    else:
        return sign_in_data_not_match()


# 사용자 정보 갱신
def user_update(db_session, request: Request, user: UserUpdateRequest):
    token = request.headers.get("authorized-key")
    if token is None:
        return invalid_jwt()
    token_data = decode_token(token)

    if token_data["email"] == user.email:
        data = db_session.query(User).filter(user.email == User.email).first()
        if data:
            if user.username is not None:
                data.username = user.username
            if user.password is not None:
                if bool(re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*()-+=]).{8,}$", user.password)):
                    salt = bcrypt.gensalt()
                    data.salt = salt
                    data.password = bcrypt.hashpw(user.password.encode("utf-8"), salt)
                else:
                    return password_rule_violation()

            db_session.commit()
            db_session.refresh(data)
            return success_response({"user_id": data.id})
        else:
            return not_found()
    else:
        return jwt_data_not_match()


def token_refresh(request: Request, email: str):
    data = decode_token(request.headers.get("authorized-key"))
    if type(data) is dict:
        if data["email"] == email:
            return success_response({"access_token": create_access_token({"email": data["email"]})})
        else:
            return jwt_data_not_match()
    elif type(data) is int:
        if data == 1:
            return invalid_jwt()
        elif data == 2:
            return expired_jwt()
        else:
            return undefined_error()
    else:
        return undefined_error()
