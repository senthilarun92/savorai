from pydantic import BaseModel, EmailStr, Field, model_validator
import re


USERNAME_PATTERN = re.compile(r"^[a-z0-9_]+$")


class SignupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_signup(self):
        self.username = self.username.strip().lower()
        self.email = str(self.email).strip().lower()

        if not USERNAME_PATTERN.fullmatch(self.username):
            raise ValueError(
                "Username can contain only letters, numbers, and underscore"
            )

        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")

        if self.password != self.password.strip():
            raise ValueError("Password cannot start or end with spaces")

        return self


class SigninRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def normalize_identifier(self):
        self.identifier = self.identifier.strip().lower()
        return self


class UserResponse(BaseModel):
    id: int
    username: str
    name: str | None
    email: EmailStr
    email_verified: bool
