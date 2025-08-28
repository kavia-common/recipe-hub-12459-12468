#!/usr/bin/env python3
"""
Seed script to populate the database with demo users, recipes, and favorites.

This script is intended for local/dev usage to quickly bootstrap the database with
sample data for testing and demonstration purposes.

Usage:
    python -m src.scripts.seed
or
    python recipe_backend/src/scripts/seed.py

Environment:
    Uses settings from src.core.config (DATABASE_URL, etc.). Defaults will use a
    local SQLite database if not configured.

Notes:
    - The script is idempotent: it checks for existing users/recipes/favorites and
      does not duplicate them on repeated runs.
    - Passwords are hashed using the same security helper as the application.
"""

from __future__ import annotations



from sqlalchemy.orm import Session

from src.core.db import Base, engine, SessionLocal
from src.core.security import get_password_hash
from src.models.models import User, Recipe, Favorite


def _ensure_tables() -> None:
    """Create tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def _get_or_create_user(db: Session, email: str, username: str, password: str) -> User:
    """Get a user by email or username, otherwise create it."""
    user = db.query(User).filter((User.email == email) | (User.username == username)).first()
    if user:
        return user
    user = User(
        email=email,
        username=username,
        password_hash=get_password_hash(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _get_or_create_recipe(
    db: Session,
    author_id: int,
    title: str,
    description: str | None,
    ingredients: str | None,
    instructions: str | None,
    image_url: str | None,
) -> Recipe:
    """Get a recipe by author and title, otherwise create it."""
    recipe = db.query(Recipe).filter(Recipe.author_id == author_id, Recipe.title == title).first()
    if recipe:
        return recipe
    recipe = Recipe(
        title=title,
        description=description,
        ingredients=ingredients,
        instructions=instructions,
        image_url=image_url,
        author_id=author_id,
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


def _favorite_if_not_exists(db: Session, user_id: int, recipe_id: int) -> Favorite:
    """Create a favorite record if it does not already exist."""
    fav = db.query(Favorite).filter(Favorite.user_id == user_id, Favorite.recipe_id == recipe_id).first()
    if fav:
        return fav
    fav = Favorite(user_id=user_id, recipe_id=recipe_id)
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return fav


def run_seed() -> None:
    """Run the seeding process with demo data."""
    _ensure_tables()

    db: Session = SessionLocal()

    try:
        # Demo users
        alice = _get_or_create_user(db, email="alice@example.com", username="alice", password="password123")
        bob = _get_or_create_user(db, email="bob@example.com", username="bob", password="password123")
        carol = _get_or_create_user(db, email="carol@example.com", username="carol", password="password123")

        # Demo recipes (owned by different users)
        r1 = _get_or_create_recipe(
            db,
            author_id=alice.id,
            title="Classic Pancakes",
            description="Fluffy pancakes perfect for breakfast.",
            ingredients="Flour\nMilk\nEggs\nSugar\nBaking powder\nSalt\nButter",
            instructions="1. Mix dry ingredients.\n2. Add milk and eggs.\n3. Cook on griddle until golden.",
            image_url="https://images.unsplash.com/photo-1587731562136-3f0f0f3bf5d9?w=800",
        )

        r2 = _get_or_create_recipe(
            db,
            author_id=bob.id,
            title="Spaghetti Aglio e Olio",
            description="Simple Italian pasta with garlic and olive oil.",
            ingredients="Spaghetti\nGarlic\nOlive oil\nRed pepper flakes\nParsley\nSalt",
            instructions="1. Cook pasta.\n2. Sauté garlic in oil.\n3. Combine with pasta and parsley.",
            image_url="https://images.unsplash.com/photo-1521389508051-d7ffb5dc8bbf?w=800",
        )

        r3 = _get_or_create_recipe(
            db,
            author_id=carol.id,
            title="Chicken Caesar Salad",
            description="Crisp romaine with grilled chicken and Caesar dressing.",
            ingredients="Romaine\nChicken breast\nCroutons\nParmesan\nCaesar dressing\nLemon",
            instructions="1. Grill chicken.\n2. Toss romaine with dressing.\n3. Top with chicken, croutons, and parmesan.",
            image_url="https://images.unsplash.com/photo-1551892374-5d1b16f2b66b?w=800",
        )

        r4 = _get_or_create_recipe(
            db,
            author_id=alice.id,
            title="Avocado Toast Deluxe",
            description="Avocado toast with poached egg and cherry tomatoes.",
            ingredients="Sourdough bread\nAvocado\nEggs\nCherry tomatoes\nLemon\nSalt\nPepper",
            instructions="1. Toast bread.\n2. Smash avocado with lemon, salt, pepper.\n3. Top with poached egg and tomatoes.",
            image_url="https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800",
        )

        # Demo favorites
        _favorite_if_not_exists(db, user_id=alice.id, recipe_id=r2.id)
        _favorite_if_not_exists(db, user_id=bob.id, recipe_id=r1.id)
        _favorite_if_not_exists(db, user_id=bob.id, recipe_id=r3.id)
        _favorite_if_not_exists(db, user_id=carol.id, recipe_id=r1.id)
        _favorite_if_not_exists(db, user_id=carol.id, recipe_id=r2.id)
        _favorite_if_not_exists(db, user_id=carol.id, recipe_id=r4.id)

        # Summary output
        users_count = db.query(User).count()
        recipes_count = db.query(Recipe).count()
        favorites_count = db.query(Favorite).count()
        print(f"Seed complete. Users={users_count}, Recipes={recipes_count}, Favorites={favorites_count}")

        # Helpful credentials for local testing
        print("Test accounts:")
        print("  alice / password123")
        print("  bob   / password123")
        print("  carol / password123")

    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
