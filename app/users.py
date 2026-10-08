from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.post("")
def create_user(user_data: dict, db: Session = Depends(get_db)):
    name = user_data.get("name")
    email = user_data.get("email")

    if not name or not email:
        raise HTTPException(
            status_code=400,
            detail="name and email are required"
        )

    existing_user = db.query(User).filter(User.email == email).first()

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="User already exists"
        )

    user = User(
        name=name,
        email=email
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "User created successfully",
        "id": user.id,
        "name": user.name,
        "email": user.email
    }
