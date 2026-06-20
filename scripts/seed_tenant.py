import asyncio
import uuid
import sys
import os

# make sure app/ is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passlib.context import CryptContext
from app.db.models import Tenant
from app.db.session import get_db, run_migrations
from sqlalchemy.exc import IntegrityError

pwd_ctx = CryptContext(schemes=["bcrypt"])


async def seed():
    # ensure tables exist
    await run_migrations()
    async with get_db() as db:
        # local API key string (don't shadow names from imports)
        api_key_value = "demo-api-key-12345"
        # bcrypt limits input to 72 bytes; truncate before hashing
        api_key_hash = pwd_ctx.hash(api_key_value[:72])

        tenant = Tenant(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            name="Demo Legal Firm",
            plan="pro",
            api_key_hash=api_key_hash,
        )
        try:
            db.add(tenant)
            await db.commit()
            print("\n✅ Tenant seeded successfully.")
            print("   Name    : Demo Legal Firm")
            print(f"   API key : {api_key_value}")
            print("   Tenant ID: 00000000-0000-0000-0000-000000000001\n")
        except IntegrityError as e:
            if "unique" in str(e).lower():
                print("Tenant already exists, skipping.")
            else:
                raise


if __name__ == "__main__":
    asyncio.run(seed())