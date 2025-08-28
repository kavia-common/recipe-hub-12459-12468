from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# Common
class MessageResponse(BaseModel):
    message: str = Field(..., description="Human readable message")


# User Schemas
class UserBase(BaseModel):
    email: EmailStr = Field(..., description="User email")
    username: str = Field(..., description="Unique username", max_length=50)


class UserCreate(UserBase):
    password: str = Field(..., description="Plain password for account creation", min_length=6)


class UserLogin(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class UserRead(UserBase):
    id: int = Field(..., description="User identifier")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


# Auth Schemas
class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Type of token")


# Recipe Schemas
class RecipeBase(BaseModel):
    title: str = Field(..., description="Recipe title", max_length=200)
    description: Optional[str] = Field(None, description="Recipe description")
    ingredients: Optional[str] = Field(None, description="Ingredients as text, newline separated")
    instructions: Optional[str] = Field(None, description="Instructions as text, newline separated")
    image_url: Optional[str] = Field(None, description="URL to the recipe image")


class RecipeCreate(RecipeBase):
    pass


class RecipeUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Recipe title", max_length=200)
    description: Optional[str] = Field(None, description="Recipe description")
    ingredients: Optional[str] = Field(None, description="Ingredients as text, newline separated")
    instructions: Optional[str] = Field(None, description="Instructions as text, newline separated")
    image_url: Optional[str] = Field(None, description="URL to the recipe image")


class RecipeRead(RecipeBase):
    id: int = Field(..., description="Recipe identifier")
    author_id: int = Field(..., description="Author user id")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


# Favorite Schemas
class FavoriteCreate(BaseModel):
    recipe_id: int = Field(..., description="Recipe id to favorite")


class FavoriteRead(BaseModel):
    id: int = Field(..., description="Favorite identifier")
    user_id: int = Field(..., description="User id")
    recipe_id: int = Field(..., description="Recipe id")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True
