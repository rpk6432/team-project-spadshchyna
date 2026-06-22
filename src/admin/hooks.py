from sqlalchemy import func, select, update

from database import async_session
from models.homestead import Homestead
from models.review import Review


async def recalc_homestead_rating(homestead_id: int) -> None:
    """Recalculate rating and review_count for a homestead."""
    async with async_session() as session:
        result = await session.execute(
            select(
                func.coalesce(func.avg(Review.rating), 0.0),
                func.count(Review.id),
            ).where(Review.homestead_id == homestead_id)
        )
        avg_rating, count = result.one()
        await session.execute(
            update(Homestead)
            .where(Homestead.id == homestead_id)
            .values(rating=round(float(avg_rating), 2), review_count=count)
        )
        await session.commit()
