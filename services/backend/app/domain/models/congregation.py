from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

# weekday: 0=Mo, 1=Di, 2=Mi, 3=Do, 4=Fr, 5=Sa, 6=So  (Python-Konvention)
DEFAULT_SERVICE_TIMES: list[dict] = [
    {"weekday": 6, "time": "09:30"},  # Sonntag
    {"weekday": 2, "time": "20:00"},  # Mittwoch
]


@dataclass
class Congregation:
    id: uuid.UUID
    name: str
    district_id: uuid.UUID
    service_times: list[dict]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        name: str,
        district_id: uuid.UUID,
        service_times: list[dict] | None = None,
    ) -> Congregation:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid.uuid4(),
            name=name,
            district_id=district_id,
            service_times=service_times if service_times is not None else list(DEFAULT_SERVICE_TIMES),
            created_at=now,
            updated_at=now,
        )
