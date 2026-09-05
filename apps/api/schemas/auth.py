from pydantic import BaseModel, EmailStr

class UserSignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str | None = None
