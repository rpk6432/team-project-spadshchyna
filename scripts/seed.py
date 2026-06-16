"""Idempotent seed script -- populates DB with demo data."""

import asyncio

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from models import Amenity, Homestead, Host, Region, Review, User

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
    "Herbal remedies",
    "Stargazing",
    "Berry picking",
    "Mushroom foraging",
    "Bread baking",
    "Weaving workshop",
    "Cheese making",
    "Wine tasting",
    "River swimming",
    "Mountain hiking",
    "Orchard walks",
    "Handmade soap",
    "Candle making",
    "Woodcarving",
    "Photography spots",
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

HOMESTEADS = [
    {
        "name": "Cossack Heritage Estate",
        "region": "carpathians",
        "host_idx": 0,
        "description": (
            "Step back in time and experience the spirit of Cossack heritage "
            "in this beautifully restored 19th-century estate. Handcrafted wooden "
            "architecture, traditional furnishings, and authentic details create a "
            "unique atmosphere of history and comfort."
        ),
        "price_per_night": 2800,
        "base_guests": 2,
        "extra_guest_fee": 400,
        "max_guests": 6,
        "cleaning_fee": 500,
        "bedrooms": 3,
        "beds": 4,
        "bathrooms": 2,
        "amenities": [
            "Traditional stove",
            "Heritage tours",
            "Historic vibe",
            "Folk storytelling",
            "Wooden architecture",
            "Garden & meadow",
            "Local cuisine",
            "Birdwatching",
            "Bread baking",
            "Photography spots",
        ],
    },
    {
        "name": "Polissia Woodland Retreat",
        "region": "polissia",
        "host_idx": 1,
        "description": (
            "A secluded wooden cabin surrounded by ancient forests and wetlands. "
            "Wake up to birdsong, explore hidden trails, and enjoy evenings "
            "by the bonfire under a canopy of stars."
        ),
        "price_per_night": 1800,
        "base_guests": 2,
        "extra_guest_fee": 300,
        "max_guests": 4,
        "cleaning_fee": 350,
        "bedrooms": 2,
        "beds": 2,
        "bathrooms": 1,
        "amenities": [
            "Birdwatching",
            "Fishing",
            "Bonfire area",
            "Garden & meadow",
            "Wooden architecture",
            "Mushroom foraging",
            "Stargazing",
            "Berry picking",
            "River swimming",
        ],
    },
    {
        "name": "Podillia Pottery House",
        "region": "podillia",
        "host_idx": 2,
        "description": (
            "A charming homestead in the heart of Podillia's rolling hills. "
            "Learn the art of traditional pottery, taste home-cooked meals, "
            "and explore sunflower fields stretching to the horizon."
        ),
        "price_per_night": 2200,
        "base_guests": 2,
        "extra_guest_fee": 350,
        "max_guests": 5,
        "cleaning_fee": 400,
        "bedrooms": 2,
        "beds": 3,
        "bathrooms": 1,
        "amenities": [
            "Pottery workshop",
            "Local cuisine",
            "Garden & meadow",
            "Heritage tours",
            "Traditional stove",
            "Bread baking",
            "Orchard walks",
            "Handmade soap",
            "Photography spots",
        ],
    },
    {
        "name": "Black Sea Fisherman's Lodge",
        "region": "black-sea-coast",
        "host_idx": 0,
        "description": (
            "A rustic seaside lodge where fishing traditions meet coastal charm. "
            "Fresh catch every morning, boat trips at sunset, and stories "
            "from generations of local fishermen."
        ),
        "price_per_night": 3200,
        "base_guests": 2,
        "extra_guest_fee": 500,
        "max_guests": 6,
        "cleaning_fee": 600,
        "bedrooms": 3,
        "beds": 4,
        "bathrooms": 2,
        "amenities": [
            "Fishing",
            "Local cuisine",
            "Bonfire area",
            "Heritage tours",
            "Folk storytelling",
            "Stargazing",
            "Photography spots",
            "Bread baking",
            "River swimming",
        ],
    },
    {
        "name": "Carpathian Bee Garden",
        "region": "carpathians",
        "host_idx": 1,
        "description": (
            "Nestled among alpine meadows, this homestead is home to a thriving "
            "apiary. Taste fresh honey, learn beekeeping secrets, and hike "
            "through wildflower trails with mountain views."
        ),
        "price_per_night": 2400,
        "base_guests": 2,
        "extra_guest_fee": 350,
        "max_guests": 4,
        "cleaning_fee": 400,
        "bedrooms": 2,
        "beds": 2,
        "bathrooms": 1,
        "amenities": [
            "Beekeeping",
            "Garden & meadow",
            "Birdwatching",
            "Traditional stove",
            "Local cuisine",
            "Mountain hiking",
            "Berry picking",
            "Herbal remedies",
            "Bread baking",
        ],
    },
    {
        "name": "Embroidery Manor",
        "region": "podillia",
        "host_idx": 2,
        "description": (
            "A lovingly preserved manor where every room tells a story through "
            "hand-embroidered textiles. Join workshops, walk through herb gardens, "
            "and experience the living tradition of Ukrainian needlework."
        ),
        "price_per_night": 2600,
        "base_guests": 2,
        "extra_guest_fee": 400,
        "max_guests": 5,
        "cleaning_fee": 450,
        "bedrooms": 3,
        "beds": 3,
        "bathrooms": 2,
        "amenities": [
            "Embroidery class",
            "Garden & meadow",
            "Historic vibe",
            "Traditional music",
            "Local cuisine",
            "Weaving workshop",
            "Candle making",
            "Herbal remedies",
            "Orchard walks",
        ],
    },
    {
        "name": "Hutsul Highland Hut",
        "region": "carpathians",
        "host_idx": 0,
        "description": (
            "A traditional Hutsul wooden hut high in the Carpathian mountains. "
            "Enjoy folk music evenings, horseback rides through highland pastures, "
            "and the warmth of a centuries-old stove."
        ),
        "price_per_night": 1900,
        "base_guests": 2,
        "extra_guest_fee": 300,
        "max_guests": 4,
        "cleaning_fee": 350,
        "bedrooms": 2,
        "beds": 2,
        "bathrooms": 1,
        "amenities": [
            "Traditional music",
            "Horse riding",
            "Traditional stove",
            "Wooden architecture",
            "Folk storytelling",
            "Mountain hiking",
            "Cheese making",
            "Bonfire area",
            "Stargazing",
        ],
    },
    {
        "name": "Polissia Herb Cottage",
        "region": "polissia",
        "host_idx": 2,
        "description": (
            "A cozy cottage surrounded by medicinal herb gardens and berry bushes. "
            "Learn about traditional herbal remedies, forage in nearby forests, "
            "and relax in the quietest corner of Ukraine."
        ),
        "price_per_night": 1600,
        "base_guests": 2,
        "extra_guest_fee": 250,
        "max_guests": 3,
        "cleaning_fee": 300,
        "bedrooms": 1,
        "beds": 2,
        "bathrooms": 1,
        "amenities": [
            "Garden & meadow",
            "Local cuisine",
            "Birdwatching",
            "Traditional stove",
            "Heritage tours",
            "Herbal remedies",
            "Mushroom foraging",
            "Berry picking",
            "Handmade soap",
        ],
    },
    {
        "name": "Coastal Vineyard Villa",
        "region": "black-sea-coast",
        "host_idx": 1,
        "description": (
            "A sun-drenched villa surrounded by grapevines on the Black Sea coast. "
            "Wine tastings, cooking classes with local produce, and lazy afternoons "
            "overlooking the sea define the experience."
        ),
        "price_per_night": 3500,
        "base_guests": 2,
        "extra_guest_fee": 500,
        "max_guests": 6,
        "cleaning_fee": 600,
        "bedrooms": 3,
        "beds": 4,
        "bathrooms": 2,
        "amenities": [
            "Local cuisine",
            "Garden & meadow",
            "Heritage tours",
            "Historic vibe",
            "Bonfire area",
            "Wine tasting",
            "Cheese making",
            "Photography spots",
            "Orchard walks",
        ],
    },
    {
        "name": "Steppe Horse Ranch",
        "region": "podillia",
        "host_idx": 0,
        "description": (
            "An open-air ranch on the Podillia steppe where horses roam free. "
            "Ride across endless grasslands, watch sunsets from the saddle, "
            "and sleep under hand-woven blankets in a traditional farmhouse."
        ),
        "price_per_night": 2100,
        "base_guests": 2,
        "extra_guest_fee": 350,
        "max_guests": 5,
        "cleaning_fee": 400,
        "bedrooms": 2,
        "beds": 3,
        "bathrooms": 1,
        "amenities": [
            "Horse riding",
            "Bonfire area",
            "Garden & meadow",
            "Folk storytelling",
            "Traditional music",
            "Stargazing",
            "Photography spots",
            "Bread baking",
            "Local cuisine",
        ],
    },
    {
        "name": "Carpathian Woodcarver's Lodge",
        "region": "carpathians",
        "host_idx": 2,
        "description": (
            "Every beam and doorframe in this lodge is hand-carved by local masters. "
            "Watch artisans at work, try your hand at woodcarving, and explore "
            "the surrounding spruce forests on guided nature walks."
        ),
        "price_per_night": 2700,
        "base_guests": 2,
        "extra_guest_fee": 400,
        "max_guests": 5,
        "cleaning_fee": 500,
        "bedrooms": 2,
        "beds": 3,
        "bathrooms": 1,
        "amenities": [
            "Wooden architecture",
            "Heritage tours",
            "Traditional stove",
            "Birdwatching",
            "Garden & meadow",
            "Woodcarving",
            "Mountain hiking",
            "Mushroom foraging",
            "Photography spots",
        ],
    },
    {
        "name": "Liman Reed House",
        "region": "black-sea-coast",
        "host_idx": 2,
        "description": (
            "A unique house built with traditional reed construction on the shores "
            "of a coastal liman. Kayak through wetlands, spot rare birds, "
            "and savor fresh seafood prepared the old-fashioned way."
        ),
        "price_per_night": 2000,
        "base_guests": 2,
        "extra_guest_fee": 300,
        "max_guests": 4,
        "cleaning_fee": 350,
        "bedrooms": 2,
        "beds": 2,
        "bathrooms": 1,
        "amenities": [
            "Fishing",
            "Birdwatching",
            "Local cuisine",
            "Garden & meadow",
            "Bonfire area",
            "River swimming",
            "Stargazing",
            "Photography spots",
            "Handmade soap",
        ],
    },
]

REVIEW_CATEGORIES = ["location", "cleanliness", "hospitality", "atmosphere", "value"]

REVIEWS_POOL = [
    {
        "author_name": "Anna M.",
        "country": "Germany",
        "rating": 5.0,
        "text": (
            "An unforgettable experience. The host was incredibly"
            " welcoming and the surroundings are breathtaking."
        ),
    },
    {
        "author_name": "James L.",
        "country": "United Kingdom",
        "rating": 4.5,
        "text": (
            "Loved every moment. The traditional atmosphere"
            " is authentic and the food was amazing."
        ),
    },
    {
        "author_name": "Sophie R.",
        "country": "France",
        "rating": 4.0,
        "text": (
            "A peaceful retreat far from the city."
            " The homestead has real character and charm."
        ),
    },
    {
        "author_name": "Tomasz K.",
        "country": "Poland",
        "rating": 5.0,
        "text": (
            "Best trip we've ever taken. The cultural activities"
            " were a highlight for the whole family."
        ),
    },
    {
        "author_name": "Maria S.",
        "country": "Ukraine",
        "rating": 4.5,
        "text": (
            "Felt like visiting grandparents in the countryside."
            " Genuine hospitality and delicious food."
        ),
    },
    {
        "author_name": "Erik N.",
        "country": "Sweden",
        "rating": 4.0,
        "text": (
            "Quiet and beautiful. Exactly what we needed to disconnect and recharge."
        ),
    },
    {
        "author_name": "Isabella C.",
        "country": "Italy",
        "rating": 5.0,
        "text": (
            "The attention to heritage details is remarkable."
            " A truly unique place to stay."
        ),
    },
    {
        "author_name": "David W.",
        "country": "Canada",
        "rating": 4.5,
        "text": (
            "We came for two nights and wished we'd booked a week. Highly recommended."
        ),
    },
    {
        "author_name": "Katja B.",
        "country": "Austria",
        "rating": 4.0,
        "text": (
            "Great location and very clean. The hosts go above"
            " and beyond to make you feel at home."
        ),
    },
    {
        "author_name": "Olha P.",
        "country": "Ukraine",
        "rating": 5.0,
        "text": (
            "A hidden gem. The workshops were so much fun"
            " and the nature around is stunning."
        ),
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


async def seed_homesteads(
    db: AsyncSession,
    regions: dict[str, Region],
    amenities: dict[str, Amenity],
    hosts: list[Host],
) -> list[Homestead]:
    homesteads: list[Homestead] = []
    for data in HOMESTEADS:
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
            description=data["description"],
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
            review_data = REVIEWS_POOL[(i * 3 + j) % len(REVIEWS_POOL)]
            category = REVIEW_CATEGORIES[j % len(REVIEW_CATEGORIES)]
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


# Main


async def main() -> None:
    async with session_factory() as db:
        print("Seeding admin user...")
        await get_or_create_user(db)

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

        await db.commit()
        print("\nDone! All data seeded.")


if __name__ == "__main__":
    asyncio.run(main())
