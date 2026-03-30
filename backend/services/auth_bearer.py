from typing import Annotated

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.services.auth import decode_token


async def verify_jwt(token: str) -> bool:
    decoded_token = await decode_token(token)
    return True if decoded_token else False


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(
            JWTBearer, self
        ).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=403, detail="Invalid authentication scheme"
                )
            if not await verify_jwt(credentials.credentials):
                raise HTTPException(
                    status_code=403, detail="Invalid token or expired token"
                )
            return credentials.credentials
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code")


security_scheme = JWTBearer()


async def get_current_user_id(token: Annotated[str, Depends(security_scheme)]) -> int:
    decoded_token = await decode_token(token)
    if not decoded_token or "user_id" not in decoded_token:
        raise HTTPException(status_code=403, detail="Invalid token payload")
    return decoded_token["user_id"]
