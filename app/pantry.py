from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.pantry_models import PantryItem
from app.models import User

router = APIRouter(prefix="/api/pantry", tags=["Pantry"])


@router.post("")
def add_pantry_item(data: dict, db: Session = Depends(get_db)):
    user_id = data.get("user_id")
    ingredient = data.get("ingredient")
    quantity = data.get("quantity")
    category = data.get("category")

    if not user_id or not ingredient:
        raise HTTPException(
            status_code=400,
            detail="user_id and ingredient are required"
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    pantry_item = PantryItem(
        user_id=user_id,
        ingredient=ingredient,
        quantity=quantity,
        category=category
    )

    db.add(pantry_item)
    db.commit()
    db.refresh(pantry_item)

    return {
        "message": "Pantry item added successfully",
        "id": pantry_item.id,
        "user_id": pantry_item.user_id,
        "ingredient": pantry_item.ingredient,
        "quantity": pantry_item.quantity,
        "category": pantry_item.category
    }


@router.get("/{user_id}")
def get_pantry_items(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    pantry_items = (
        db.query(PantryItem)
        .filter(PantryItem.user_id == user_id)
        .order_by(PantryItem.created_at.desc())
        .all()
    )

    return [
        {
            "id": item.id,
            "ingredient": item.ingredient,
            "quantity": item.quantity,
            "category": item.category,
            "created_at": item.created_at
        }
        for item in pantry_items
    ]


@router.delete("/{user_id}/{item_id}")
def delete_pantry_item(
    user_id: int,
    item_id: int,
    db: Session = Depends(get_db)
):
    pantry_item = db.query(PantryItem).filter(
        PantryItem.id == item_id,
        PantryItem.user_id == user_id
    ).first()

    if not pantry_item:
        raise HTTPException(
            status_code=404,
            detail="Pantry item not found"
        )

    db.delete(pantry_item)
    db.commit()

    return {
        "message": "Pantry item deleted successfully",
        "user_id": user_id,
        "item_id": item_id
    }
