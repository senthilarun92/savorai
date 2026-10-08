from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.shopping_models import ShoppingItem
from app.models import User

router = APIRouter(prefix="/api/shopping-list", tags=["Shopping List"])


@router.post("")
def add_shopping_item(data: dict, db: Session = Depends(get_db)):
    user_id = data.get("user_id")
    ingredient = data.get("ingredient")
    quantity = data.get("quantity")

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

    shopping_item = ShoppingItem(
        user_id=user_id,
        ingredient=ingredient,
        quantity=quantity,
        is_purchased=False
    )

    db.add(shopping_item)
    db.commit()
    db.refresh(shopping_item)

    return {
        "message": "Shopping item added successfully",
        "id": shopping_item.id,
        "user_id": shopping_item.user_id,
        "ingredient": shopping_item.ingredient,
        "quantity": shopping_item.quantity,
        "is_purchased": shopping_item.is_purchased
    }


@router.get("/{user_id}")
def get_shopping_items(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    shopping_items = (
        db.query(ShoppingItem)
        .filter(ShoppingItem.user_id == user_id)
        .order_by(ShoppingItem.created_at.desc())
        .all()
    )

    return [
        {
            "id": item.id,
            "ingredient": item.ingredient,
            "quantity": item.quantity,
            "is_purchased": item.is_purchased,
            "created_at": item.created_at
        }
        for item in shopping_items
    ]


@router.put("/{user_id}/{item_id}/purchase")
def mark_as_purchased(
    user_id: int,
    item_id: int,
    db: Session = Depends(get_db)
):
    shopping_item = db.query(ShoppingItem).filter(
        ShoppingItem.id == item_id,
        ShoppingItem.user_id == user_id
    ).first()

    if not shopping_item:
        raise HTTPException(
            status_code=404,
            detail="Shopping item not found"
        )

    shopping_item.is_purchased = True

    db.commit()
    db.refresh(shopping_item)

    return {
        "message": "Shopping item marked as purchased",
        "id": shopping_item.id,
        "user_id": shopping_item.user_id,
        "ingredient": shopping_item.ingredient,
        "quantity": shopping_item.quantity,
        "is_purchased": shopping_item.is_purchased
    }


@router.delete("/{user_id}/{item_id}")
def delete_shopping_item(
    user_id: int,
    item_id: int,
    db: Session = Depends(get_db)
):
    shopping_item = db.query(ShoppingItem).filter(
        ShoppingItem.id == item_id,
        ShoppingItem.user_id == user_id
    ).first()

    if not shopping_item:
        raise HTTPException(
            status_code=404,
            detail="Shopping item not found"
        )

    db.delete(shopping_item)
    db.commit()

    return {
        "message": "Shopping item deleted successfully",
        "user_id": user_id,
        "item_id": item_id
    }
