"""Idempotent seed script -- populates DB with demo data."""

import asyncio

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from models import Amenity, Host, Region, User

engine = create_async_engine(settings.database_url)
session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Data

ADMIN = {
    "first_name": "Admin",
    "last_name": "Spadshchyna",
    "email": "admin@spadshchyna.ua",
    "password": "admin123",
    "is_admin": True,
}

REGIONS = [
    {"name": "Carpathians", "slug": "carpathians"},
    {"name": "Polissia", "slug": "polissia"},
    {"name": "Podillia", "slug": "podillia"},
    {"name": "Black Sea Coast", "slug": "black-sea-coast"},
]

AMENITIES = [
    "Traditional stove",
    "Heritage tours",
    "Historic vibe",
    "Folk storytelling",
    "Wooden architecture",
    "Garden & meadow",
    "Local cuisine",
    "Birdwatching",
    "Pottery workshop",
    "Embroidery class",
    "Beekeeping",
    "Horse riding",
    "Fishing",
    "Bonfire area",
    "Traditional music",
]

HOSTS = [
    {
        "name": "Olena Kovalenko",
        "email": "olena@example.com",
        "languages": ["uk", "en"],
    },
    {
        "name": "Mykola Shevchenko",
        "email": "mykola@example.com",
        "languages": ["uk", "en", "pl"],
    },
    {
        "name": "Iryna Bondarenko",
        "email": "iryna@example.com",
        "languages": ["uk", "de"],
    },
]

# Helpers


async def get_or_create_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.email == ADMIN["email"]))
    user = result.scalar_one_or_none()
    if user:
        print(f"  [ok] Admin already exists: {user.email}")
        return user

    password_hash = bcrypt.hashpw(ADMIN["password"].encode(), bcrypt.gensalt()).decode()
    user = User(
        first_name=ADMIN["first_name"],
        last_name=ADMIN["last_name"],
        email=ADMIN["email"],
        password_hash=password_hash,
        is_admin=ADMIN["is_admin"],
    )
    db.add(user)
    await db.flush()
    print(f"  [+] Created admin: {user.email}")
    return user


async def seed_regions(db: AsyncSession) -> dict[str, Region]:
    regions: dict[str, Region] = {}
    for data in REGIONS:
        result = await db.execute(select(Region).where(Region.slug == data["slug"]))
        region = result.scalar_one_or_none()
        if region:
            print(f"  [ok] Region exists: {region.name}")
        else:
            region = Region(**data)
            db.add(region)
            await db.flush()
            print(f"  [+] Created region: {region.name}")
        regions[data["slug"]] = region
    return regions


async def seed_amenities(db: AsyncSession) -> dict[str, Amenity]:
    amenities: dict[str, Amenity] = {}
    for name in AMENITIES:
        result = await db.execute(select(Amenity).where(Amenity.name == name))
        amenity = result.scalar_one_or_none()
        if amenity:
            print(f"  [ok] Amenity exists: {name}")
        else:
            amenity = Amenity(name=name)
            db.add(amenity)
            await db.flush()
            print(f"  [+] Created amenity: {name}")
        amenities[name] = amenity
    return amenities


async def seed_hosts(db: AsyncSession) -> list[Host]:
    hosts: list[Host] = []
    for data in HOSTS:
        result = await db.execute(select(Host).where(Host.email == data["email"]))
        host = result.scalar_one_or_none()
        if host:
            print(f"  [ok] Host exists: {host.name}")
        else:
            host = Host(**data)
            db.add(host)
            await db.flush()
            print(f"  [+] Created host: {host.name}")
        hosts.append(host)
    return hosts


# Main


async def main() -> None:
    async with session_factory() as db:
        print("Seeding admin user...")
        await get_or_create_user(db)

        print("Seeding regions...")
        await seed_regions(db)

        print("Seeding amenities...")
        await seed_amenities(db)

        print("Seeding hosts...")
        await seed_hosts(db)

        await db.commit()
        print("\nDone! Base data seeded.")


if __name__ == "__main__":
    asyncio.run(main())
