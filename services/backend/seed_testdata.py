from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.adapters.db.repositories.congregation import SqlCongregationRepository
from app.adapters.db.repositories.district import SqlDistrictRepository
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.adapters.db.session import AsyncSessionLocal
from app.domain.models.congregation import Congregation
from app.domain.models.district import District
from app.domain.models.leader import Leader, LeaderRank, SpecialRole


@dataclass(frozen=True)
class LeaderSeed:
    name: str
    rank: LeaderRank
    congregation_name: str | None = None
    special_role: SpecialRole | None = None


@dataclass(frozen=True)
class DistrictSeed:
    name: str
    state_code: str
    congregations: list[str]
    leaders: list[LeaderSeed]


SEED_DATA: list[DistrictSeed] = [
    DistrictSeed(
        name="Bezirk Stuttgart-Mitte",
        state_code="BW",
        congregations=["Stuttgart-Nord", "Stuttgart-West", "Ludwigsburg"],
        leaders=[
            LeaderSeed(
                name="Markus Weber",
                rank=LeaderRank.BEZIRKSAELTESTER,
                special_role=SpecialRole.BEZIRKSVORSTEHER,
            ),
            LeaderSeed(
                name="Daniel Hoffmann",
                rank=LeaderRank.PRIESTER,
                congregation_name="Stuttgart-Nord",
                special_role=SpecialRole.GEMEINDEVORSTEHER,
            ),
            LeaderSeed(
                name="Tobias Schenk",
                rank=LeaderRank.PRIESTER,
                congregation_name="Stuttgart-West",
                special_role=SpecialRole.GEMEINDEVORSTEHER,
            ),
            LeaderSeed(
                name="Stefan Bauer",
                rank=LeaderRank.EVANGELIST,
                congregation_name="Ludwigsburg",
            ),
        ],
    ),
    DistrictSeed(
        name="Bezirk Frankfurt",
        state_code="HE",
        congregations=["Frankfurt-Innenstadt", "Offenbach", "Bad Homburg"],
        leaders=[
            LeaderSeed(
                name="Johannes Keller",
                rank=LeaderRank.BEZIRKSEVANGELIST,
                special_role=SpecialRole.BEZIRKSVORSTEHER,
            ),
            LeaderSeed(
                name="Benjamin Roth",
                rank=LeaderRank.PRIESTER,
                congregation_name="Frankfurt-Innenstadt",
                special_role=SpecialRole.GEMEINDEVORSTEHER,
            ),
            LeaderSeed(
                name="Michael Hartmann",
                rank=LeaderRank.PRIESTER,
                congregation_name="Offenbach",
            ),
            LeaderSeed(
                name="Lukas Neumann",
                rank=LeaderRank.DIAKON,
                congregation_name="Bad Homburg",
            ),
        ],
    ),
    DistrictSeed(
        name="Bezirk Hamburg",
        state_code="HH",
        congregations=["Hamburg-Mitte", "Hamburg-Altona", "Norderstedt"],
        leaders=[
            LeaderSeed(
                name="Andreas Vogel",
                rank=LeaderRank.HIRTE,
                special_role=SpecialRole.BEZIRKSVORSTEHER,
            ),
            LeaderSeed(
                name="Sebastian Krause",
                rank=LeaderRank.PRIESTER,
                congregation_name="Hamburg-Mitte",
                special_role=SpecialRole.GEMEINDEVORSTEHER,
            ),
            LeaderSeed(
                name="Patrick Schmitt",
                rank=LeaderRank.EVANGELIST,
                congregation_name="Hamburg-Altona",
            ),
            LeaderSeed(
                name="Florian Schulz",
                rank=LeaderRank.DIAKON,
                congregation_name="Norderstedt",
            ),
        ],
    ),
]


REQUIRED_TABLES = ("districts", "congregations", "leaders")


async def _ensure_required_tables_exist(session) -> None:
    missing_tables: list[str] = []
    for table_name in REQUIRED_TABLES:
        result = await session.execute(
            text("SELECT to_regclass(:table_name)"), {"table_name": table_name}
        )
        exists = result.scalar_one()
        if exists is None:
            missing_tables.append(table_name)

    if missing_tables:
        missing = ", ".join(missing_tables)
        raise RuntimeError(
            "Fehlende Tabellen in der Datenbank: "
            f"{missing}. Bitte zuerst Migrationen ausfuehren: `uv run alembic upgrade head` "
            "(oder in Docker: `docker compose run --no-deps --rm backend alembic upgrade head`)."
        )


async def seed_test_data(*, dry_run: bool = False) -> None:
    async with AsyncSessionLocal() as session:
        await _ensure_required_tables_exist(session)

        district_repo = SqlDistrictRepository(session)
        congregation_repo = SqlCongregationRepository(session)
        leader_repo = SqlLeaderRepository(session)

        existing_districts = {d.name: d for d in await district_repo.list_all()}

        created_districts = 0
        created_congregations = 0
        created_leaders = 0

        for district_seed in SEED_DATA:
            district = existing_districts.get(district_seed.name)
            if district is None:
                district = District.create(
                    name=district_seed.name, state_code=district_seed.state_code
                )
                created_districts += 1
            else:
                district.state_code = district_seed.state_code

            await district_repo.save(district)

            existing_congregations = {
                c.name: c for c in await congregation_repo.list_by_district(district.id)
            }
            congregations_by_name: dict[str, Congregation] = {}

            for congregation_name in district_seed.congregations:
                congregation = existing_congregations.get(congregation_name)
                if congregation is None:
                    congregation = Congregation.create(
                        name=congregation_name, district_id=district.id
                    )
                    created_congregations += 1

                await congregation_repo.save(congregation)
                congregations_by_name[congregation.name] = congregation

            existing_leaders = {
                (leader.name, leader.congregation_id): leader
                for leader in await leader_repo.list_by_district(district.id)
            }

            for leader_seed in district_seed.leaders:
                congregation_id = None
                if leader_seed.congregation_name is not None:
                    congregation = congregations_by_name.get(leader_seed.congregation_name)
                    if congregation is None:
                        raise ValueError(
                            "Leader refers to unknown congregation "
                            f"'{leader_seed.congregation_name}' in district '{district.name}'"
                        )
                    congregation_id = congregation.id

                key = (leader_seed.name, congregation_id)
                leader = existing_leaders.get(key)
                if leader is None:
                    leader = Leader.create(
                        name=leader_seed.name,
                        district_id=district.id,
                        congregation_id=congregation_id,
                        rank=leader_seed.rank,
                        special_role=leader_seed.special_role,
                    )
                    created_leaders += 1
                else:
                    leader.rank = leader_seed.rank
                    leader.special_role = leader_seed.special_role
                    leader.is_active = True

                await leader_repo.save(leader)

        if dry_run:
            await session.rollback()
            action = "Dry-run"
        else:
            await session.commit()
            action = "Seed"

        print(
            f"{action} abgeschlossen: "
            f"{created_districts} Bezirke, "
            f"{created_congregations} Gemeinden, "
            f"{created_leaders} Amtstraeger neu erstellt."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed test data for districts, congregations and leaders"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate seeding and rollback at the end",
    )
    return parser.parse_args()


if __name__ == "__main__":
    import asyncio

    args = parse_args()
    try:
        asyncio.run(seed_test_data(dry_run=args.dry_run))
    except (RuntimeError, ProgrammingError) as exc:
        raise SystemExit(str(exc)) from exc
