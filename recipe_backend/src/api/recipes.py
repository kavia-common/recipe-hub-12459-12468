from __future__ import annotations

from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, exc

from src.core.db import get_db
from src.models.models import Recipe, User, Favorite
from src.schemas.schemas import (
    RecipeCreate,
    RecipeRead,
    RecipeUpdate,
    MessageResponse,
    FavoriteRead,
)
from src.api.auth import get_current_user

router = APIRouter(prefix="/recipes", tags=["Recipes"])


def _apply_filters(
    query,
    q: Optional[str] = None,
    title: Optional[str] = None,
    ingredient: Optional[str] = None,
    author_id: Optional[int] = None,
):
    """Apply filtering and search on base Recipe query."""
    if author_id is not None:
        query = query.filter(Recipe.author_id == author_id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(Recipe.title.ilike(like), Recipe.ingredients.ilike(like))
        )
    if title:
        query = query.filter(Recipe.title.ilike(f"%{title}%"))
    if ingredient:
        query = query.filter(Recipe.ingredients.ilike(f"%{ingredient}%"))
    return query


@router.get(
    "",
    response_model=List[RecipeRead],
    summary="List recipes",
    description="Retrieve a paginated list of recipes with optional search and filtering.",
    responses={
        200: {"description": "List returned"},
    },
)
def list_recipes(
    db: Annotated[Session, Depends(get_db)],
    q: Optional[str] = Query(None, description="Search text across title and ingredients"),
    title: Optional[str] = Query(None, description="Filter by title (contains)"),
    ingredient: Optional[str] = Query(None, description="Filter by ingredient (contains)"),
    author_id: Optional[int] = Query(None, description="Filter by author id"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
):
    """Return recipes with basic pagination and text search in title/ingredients."""
    query = db.query(Recipe)
    query = _apply_filters(query, q=q, title=title, ingredient=ingredient, author_id=author_id)
    query = query.order_by(Recipe.created_at.desc())
    items = query.offset(skip).limit(limit).all()
    return items


@router.get(
    "/{recipe_id}",
    response_model=RecipeRead,
    summary="Get recipe by id",
    description="Retrieve details of a recipe by its identifier.",
    responses={
        200: {"description": "Recipe found"},
        404: {"description": "Recipe not found", "model": MessageResponse},
    },
)
def get_recipe(recipe_id: int, db: Annotated[Session, Depends(get_db)]):
    """Return a single recipe by id."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    return recipe


@router.post(
    "",
    response_model=RecipeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create recipe",
    description="Create a new recipe linked to the authenticated user. Provide a minimal image_url or leave None.",
    responses={
        201: {"description": "Recipe created"},
        401: {"description": "Not authenticated", "model": MessageResponse},
    },
)
def create_recipe(
    payload: RecipeCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Create a recipe owned by the current user."""
    recipe = Recipe(
        title=payload.title,
        description=payload.description,
        ingredients=payload.ingredients,
        instructions=payload.instructions,
        image_url=payload.image_url,  # minimal image URL field (stub for uploads)
        author_id=current_user.id,
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.put(
    "/{recipe_id}",
    response_model=RecipeRead,
    summary="Update recipe",
    description="Update a recipe. Only the owner can edit.",
    responses={
        200: {"description": "Recipe updated"},
        401: {"description": "Not authenticated", "model": MessageResponse},
        403: {"description": "Forbidden, not owner", "model": MessageResponse},
        404: {"description": "Recipe not found", "model": MessageResponse},
    },
)
def update_recipe(
    recipe_id: int,
    payload: RecipeUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Update the given recipe fields if the current user is the owner."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    if recipe.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the owner of this recipe")

    update_data = payload.dict(exclude_unset=True)
    for k, v in update_data.items():
        setattr(recipe, k, v)

    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.delete(
    "/{recipe_id}",
    response_model=MessageResponse,
    summary="Delete recipe",
    description="Delete a recipe by id. Only the owner can delete.",
    responses={
        200: {"description": "Recipe deleted"},
        401: {"description": "Not authenticated", "model": MessageResponse},
        403: {"description": "Forbidden, not owner", "model": MessageResponse},
        404: {"description": "Recipe not found", "model": MessageResponse},
    },
)
def delete_recipe(
    recipe_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Delete a recipe by id if current user is the owner."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    if recipe.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the owner of this recipe")

    db.delete(recipe)
    db.commit()
    return MessageResponse(message="Recipe deleted successfully")


@router.post(
    "/{recipe_id}/favorite",
    response_model=FavoriteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Mark recipe as favorite",
    description="Mark the specified recipe as a favorite for the authenticated user. Idempotent: returns existing favorite if already favorited.",
    tags=["Recipes", "Favorites"],
    responses={
        201: {"description": "Marked as favorite"},
        200: {"description": "Already a favorite, returning existing favorite"},
        401: {"description": "Not authenticated", "model": MessageResponse},
        404: {"description": "Recipe not found", "model": MessageResponse},
    },
)
def favorite_recipe(
    recipe_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Create or return a Favorite record for the current user and the given recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    # Check existing favorite to keep idempotency
    existing = (
        db.query(Favorite)
        .filter(and_(Favorite.user_id == current_user.id, Favorite.recipe_id == recipe_id))
        .first()
    )
    if existing:
        # Return 200 OK with existing favorite
        return existing

    favorite = Favorite(user_id=current_user.id, recipe_id=recipe_id)
    db.add(favorite)
    try:
        db.commit()
    except exc.IntegrityError:
        # In rare race conditions, the unique constraint might trigger
        db.rollback()
        existing = (
            db.query(Favorite)
            .filter(and_(Favorite.user_id == current_user.id, Favorite.recipe_id == recipe_id))
            .first()
        )
        if existing:
            return existing
        raise
    db.refresh(favorite)
    return favorite


@router.delete(
    "/{recipe_id}/favorite",
    response_model=MessageResponse,
    summary="Unmark recipe as favorite",
    description="Remove the favorite mark for the specified recipe for the authenticated user. Idempotent: succeeds even if not currently favorited.",
    tags=["Recipes", "Favorites"],
    responses={
        200: {"description": "Unfavorited (or was not favorited)"},
        401: {"description": "Not authenticated", "model": MessageResponse},
        404: {"description": "Recipe not found", "model": MessageResponse},
    },
)
def unfavorite_recipe(
    recipe_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Delete the Favorite record if it exists for the user and recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    fav = (
        db.query(Favorite)
        .filter(and_(Favorite.user_id == current_user.id, Favorite.recipe_id == recipe_id))
        .first()
    )
    if fav:
        db.delete(fav)
        db.commit()
    else:
        # No-op for idempotency
        pass
    return MessageResponse(message="Recipe unfavorited")


@router.get(
    "/favorites/me",
    response_model=List[RecipeRead],
    summary="List my favorite recipes",
    description="Return a list of recipes the authenticated user has favorited.",
    tags=["Recipes", "Favorites"],
    responses={
        200: {"description": "List returned"},
        401: {"description": "Not authenticated", "model": MessageResponse},
    },
)
def list_my_favorites(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
):
    """List the current user's favorited recipes."""
    # Join favorites to recipes
    query = (
        db.query(Recipe)
        .join(Favorite, Favorite.recipe_id == Recipe.id)
        .filter(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
    )
    items = query.offset(skip).limit(limit).all()
    return items


@router.get(
    "/{recipe_id}/favorites",
    response_model=List[FavoriteRead],
    summary="List favorites for a recipe",
    description="Return list of Favorite records (user_id and metadata) for users who favorited the recipe.",
    tags=["Recipes", "Favorites"],
    responses={
        200: {"description": "List returned"},
        404: {"description": "Recipe not found", "model": MessageResponse},
    },
)
def list_favorites_for_recipe(
    recipe_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """List Favorite entries for a given recipe id."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    favs = db.query(Favorite).filter(Favorite.recipe_id == recipe_id).order_by(Favorite.created_at.desc()).all()
    return favs
