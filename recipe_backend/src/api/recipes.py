from __future__ import annotations

from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.core.db import get_db
from src.models.models import Recipe, User
from src.schemas.schemas import (
    RecipeCreate,
    RecipeRead,
    RecipeUpdate,
    MessageResponse,
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
