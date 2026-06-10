import asyncio
from app.adapters.db.repositories.district import SqlDistrictRepository
from app.adapters.db.session import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as session:
        repo = SqlDistrictRepository(session)
        districts = await repo.list_all()
        print(f"Found {len(districts)} districts")
        for d in districts:
            print(f" - {d.name}")

if __name__ == "__main__":
    asyncio.run(check())
