# Side-effect imports: register all ORM models on Base.metadata (required for Alembic autogenerate)
from app.adapters.db.orm_models.calendar_integration import CalendarIntegrationORM  # noqa: F401
from app.adapters.db.orm_models.congregation import CongregationORM  # noqa: F401
from app.adapters.db.orm_models.congregation_group import CongregationGroupORM  # noqa: F401
from app.adapters.db.orm_models.district import DistrictORM  # noqa: F401
from app.adapters.db.orm_models.event import EventORM  # noqa: F401
from app.adapters.db.orm_models.export_token import ExportTokenORM  # noqa: F401
from app.adapters.db.orm_models.leader import LeaderORM  # noqa: F401
from app.adapters.db.orm_models.service_assignment import ServiceAssignmentORM  # noqa: F401
