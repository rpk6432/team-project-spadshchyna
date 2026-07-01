"""Idempotent seed script -- populates DB with demo data."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from models import (
    Amenity,
    Booking,
    Homestead,
    HomesteadPhoto,
    Host,
    Region,
    Review,
    User,
)
from s3.client import ensure_bucket, upload_file

MEDIA_DIR = Path(__file__).parent / "seed_media"
DATA_FILE = Path(__file__).parent / "seed_data.json"

engine = create_async_engine(settings.database_url)
session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Load data

with open(DATA_FILE, encoding="utf-8") as f:
    DATA = json.load(f)

# Helpers


async def get_or_create_user(db: AsyncSession) -> User:
    admin = DATA["admin"]
    result = await db.execute(select(User).where(User.email == admin["email"]))
    user = result.scalar_one_or_none()
    if user:
        print(f"  [ok] Admin already exists: {user.email}")
        return user

    password_hash = bcrypt.hashpw(admin["password"].encode(), bcrypt.gensalt()).decode()
    user = User(
        first_name=admin["first_name"],
        last_name=admin["last_name"],
        email=admin["email"],
        password_hash=password_hash,
        is_admin=admin["is_admin"],
    )
    db.add(user)
    await db.flush()
    print(f"  [+] Created admin: {user.email}")
    return user


async def seed_regions(db: AsyncSession) -> dict[str, Region]:
    regions: dict[str, Region] = {}
    for data in DATA["regions"]:
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
    for name in DATA["amenities"]:
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
    for data in DATA["hosts"]:
        result = await db.execute(select(Host).where(Host.email == data["email"]))
        host = result.scalar_one_or_none()
        if host:
            print(f"  [ok] Host exists: {host.name}")
        else:
            host = Host(**{k: v for k, v in data.items() if k != "photo_file"})
            db.add(host)
            await db.flush()
            print(f"  [+] Created host: {host.name}")
        hosts.append(host)
    return hosts


async def seed_homesteads(
    db: AsyncSession,
    regions: dict[str, Region],
    amenities: dict[str, Amenity],
    hosts: list[Host],
) -> list[Homestead]:
    homesteads: list[Homestead] = []
    for data in DATA["homesteads"]:
        result = await db.execute(
            select(Homestead).where(Homestead.name == data["name"])
        )
        homestead = result.scalar_one_or_none()
        if homestead:
            print(f"  [ok] Homestead exists: {homestead.name}")
            homesteads.append(homestead)
            continue

        homestead = Homestead(
            host_id=hosts[data["host_idx"]].id,
            region_id=regions[data["region"]].id,
            name=data["name"],
            location=data["location"],
            description=data["description"],
            short_description=data["short_description"],
            price_per_night=data["price_per_night"],
            base_guests=data["base_guests"],
            extra_guest_fee=data["extra_guest_fee"],
            max_guests=data["max_guests"],
            cleaning_fee=data["cleaning_fee"],
            bedrooms=data["bedrooms"],
            beds=data["beds"],
            bathrooms=data["bathrooms"],
        )
        db.add(homestead)
        await db.flush()

        # link amenities
        await db.refresh(homestead, ["amenities"])
        for amenity_name in data["amenities"]:
            homestead.amenities.append(amenities[amenity_name])
        await db.flush()

        print(f"  [+] Created homestead: {homestead.name}")
        homesteads.append(homestead)
    return homesteads


async def seed_reviews(db: AsyncSession, homesteads: list[Homestead]) -> None:
    reviews_pool = DATA["reviews_pool"]
    categories = DATA["review_categories"]

    for i, homestead in enumerate(homesteads):
        existing = await db.execute(
            select(Review).where(Review.homestead_id == homestead.id)
        )
        if existing.scalars().first():
            print(f"  [ok] Reviews exist for: {homestead.name}")
            continue

        # each homestead gets 3-5 reviews, cycling through the pool
        count = 3 + (i % 3)  # 3, 4, 5, 3, 4, 5...
        total_rating = 0.0
        for j in range(count):
            review_data = reviews_pool[(i * 3 + j) % len(reviews_pool)]
            category = categories[j % len(categories)]
            review = Review(
                homestead_id=homestead.id,
                category=category,
                text=review_data["text"],
                author_name=review_data["author_name"],
                country=review_data["country"],
                rating=review_data["rating"],
            )
            db.add(review)
            total_rating += review_data["rating"]

        homestead.rating = round(total_rating / count, 1)
        homestead.review_count = count
        await db.flush()
        print(f"  [+] Added {count} reviews for: {homestead.name}")


async def seed_photos(db: AsyncSession, homesteads: list[Homestead]) -> None:
    homesteads_dir = MEDIA_DIR / "homesteads"
    if not homesteads_dir.exists():
        print("  [skip] No homesteads photos directory")
        return

    await ensure_bucket()

    for i, homestead in enumerate(homesteads, 1):
        folder = homesteads_dir / f"homestead-{i}"
        if not folder.exists():
            continue

        existing = await db.execute(
            select(HomesteadPhoto).where(HomesteadPhoto.homestead_id == homestead.id)
        )
        if existing.scalars().first():
            print(f"  [ok] Photos exist for: {homestead.name}")
            continue

        jpgs = sorted(folder.glob("*.jpg"))
        for order, jpg in enumerate(jpgs):
            key = f"homesteads/{homestead.id}/{jpg.name}"
            await upload_file(key, jpg.read_bytes())
            photo = HomesteadPhoto(
                homestead_id=homestead.id,
                url=key,
                is_main=(order == 0),
                sort_order=order,
            )
            db.add(photo)

        await db.commit()
        print(f"  [+] Uploaded {len(jpgs)} photos for: {homestead.name}")


async def seed_host_photos(db: AsyncSession, hosts: list[Host]) -> None:
    hosts_dir = MEDIA_DIR / "hosts"
    if not hosts_dir.exists():
        print("  [skip] No host photos directory")
        return

    await ensure_bucket()

    for host, data in zip(hosts, DATA["hosts"], strict=True):
        if host.photo_url:
            print(f"  [ok] Photo exists for host: {host.name}")
            continue

        photo_path = hosts_dir / data["photo_file"]
        if not photo_path.exists():
            continue

        key = f"hosts/{host.id}/{data['photo_file']}"
        await upload_file(key, photo_path.read_bytes())
        host.photo_url = key
        await db.commit()
        print(f"  [+] Uploaded photo for host: {host.name}")


# Main


async def seed_test_users(db: AsyncSession) -> dict[str, User]:
    users: dict[str, User] = {}
    for data in DATA["test_users"]:
        result = await db.execute(select(User).where(User.email == data["email"]))
        user = result.scalar_one_or_none()
        if user:
            print(f"  [ok] User exists: {user.email}")
        else:
            pw_hash = bcrypt.hashpw(
                data["password"].encode(), bcrypt.gensalt()
            ).decode()
            user = User(
                first_name=data["first_name"],
                last_name=data["last_name"],
                email=data["email"],
                password_hash=pw_hash,
            )
            db.add(user)
            await db.flush()
            print(f"  [+] Created user: {user.email}")
        users[data["email"]] = user
    return users


async def seed_bookings(
    db: AsyncSession,
    users: dict[str, User],
    homesteads: list[Homestead],
) -> None:
    from datetime import date as parse_date

    for bk in DATA["bookings"]:
        user = users[bk["user_email"]]
        hs = homesteads[bk["homestead_idx"]]
        ci = parse_date.fromisoformat(bk["check_in"])
        co = parse_date.fromisoformat(bk["check_out"])

        existing = await db.execute(
            select(Booking).where(
                Booking.user_id == user.id,
                Booking.homestead_id == hs.id,
                Booking.check_in == ci,
            )
        )
        if existing.scalar_one_or_none():
            print(f"  [ok] Booking exists: {user.email} @ {hs.name} ({ci})")
            continue

        nights = (co - ci).days
        accommodation = hs.price_per_night * nights
        extra = max(0, bk["guests"] - hs.base_guests) * hs.extra_guest_fee * nights
        subtotal = accommodation + extra + hs.cleaning_fee
        service_fee = round(subtotal * 0.10)
        donation_pct = 5.0
        donation = round(subtotal * donation_pct / 100)
        total = subtotal + service_fee + donation

        booking = Booking(
            user_id=user.id,
            homestead_id=hs.id,
            check_in=ci,
            check_out=co,
            guests=bk["guests"],
            status=bk["status"],
            accommodation_total=accommodation + extra,
            cleaning_fee=hs.cleaning_fee,
            service_fee=service_fee,
            donation_pct=donation_pct,
            donation_amount=donation,
            total=total,
            stripe_session_id=f"seed_{user.id}_{hs.id}_{ci}",
        )
        db.add(booking)
        await db.flush()
        print(f"  [+] Booking: {user.email} @ {hs.name} ({ci} → {co}) [{bk['status']}]")


async def main() -> None:
    async with session_factory() as db:
        print("Seeding admin user...")
        admin_user = await get_or_create_user(db)

        print("Seeding test users...")
        test_users = await seed_test_users(db)
        all_users = {admin_user.email: admin_user, **test_users}

        print("Seeding regions...")
        regions = await seed_regions(db)

        print("Seeding amenities...")
        amenities = await seed_amenities(db)

        print("Seeding hosts...")
        hosts = await seed_hosts(db)

        print("Seeding homesteads...")
        homesteads = await seed_homesteads(db, regions, amenities, hosts)

        print("Seeding reviews...")
        await seed_reviews(db, homesteads)

        print("Seeding bookings...")
        await seed_bookings(db, all_users, homesteads)

        await db.commit()

        print("Seeding photos...")
        await seed_photos(db, homesteads)

        print("Seeding host photos...")
        await seed_host_photos(db, hosts)

        print("\nDone! All data seeded.")


if __name__ == "__main__":
    asyncio.run(main())
