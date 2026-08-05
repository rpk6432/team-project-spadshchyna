from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exceptions import AlreadyExistsError, NotFoundError
from homesteads.schemas import HomesteadCard
from homesteads.service import to_card
from models.favourite import Favourite
from models.homestead import Homestead


async def add_favourite(db: AsyncSession, user_id: int, homestead_id: int) -> None:
    homestead = await db.execute(
        select(Homestead.id).where(
            Homestead.id == homestead_id, Homestead.is_active.is_(True)
        )
    )
    if homestead.scalar_one_or_none() is None:
        raise NotFoundError("Homestead not found")

    existing = await db.execute(
        select(Favourite.id).where(
            Favourite.user_id == user_id,
            Favourite.homestead_id == homestead_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise AlreadyExistsError("Already in favourites")

    db.add(Favourite(user_id=user_id, homestead_id=homestead_id))
    await db.commit()


async def remove_favourite(db: AsyncSession, user_id: int, homestead_id: int) -> None:
    result = await db.execute(
        select(Favourite).where(
            Favourite.user_id == user_id,
            Favourite.homestead_id == homestead_id,
        )
    )
    favourite = result.scalar_one_or_none()
    if favourite is None:
        raise NotFoundError("Favourite not found")

    await db.delete(favourite)
    await db.commit()


async def get_favourites(db: AsyncSession, user_id: int) -> list[HomesteadCard]:
    result = await db.execute(
        select(Homestead)
        .join(Favourite, Favourite.homestead_id == Homestead.id)
        .where(Favourite.user_id == user_id, Homestead.is_active.is_(True))
        .options(
            selectinload(Homestead.region),
            selectinload(Homestead.photos),
            selectinload(Homestead.amenities),
        )
        .order_by(Favourite.created_at.desc())
    )
    return [to_card(h, is_favourited=True) for h in result.scalars().all()]
