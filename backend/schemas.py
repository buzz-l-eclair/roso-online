from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    role: str

    class Config:
        from_attributes = True


class ApiKeySetRequest(BaseModel):
    service: str
    value: str = Field(min_length=1)


class ApiKeyOut(BaseModel):
    service: str
    configured: bool = True


class RunToolRequest(BaseModel):
    params: dict[str, str] = {}
