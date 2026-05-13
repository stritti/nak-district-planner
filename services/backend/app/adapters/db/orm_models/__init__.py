# Side-effect imports: register all ORM models on Base.metadata (required for Alembic autogenerate)
from app.adapters.db.orm_models.calendar_integration import CalendarIntegrationORM
from app.adapters.db.orm_models.congregation import CongregationORM
from app.adapters.db.orm_models.congregation_group import CongregationGroupORM
from app.adapters.db.orm_models.district import DistrictORM
from app.adapters.db.orm_models.event import EventORM
from app.adapters.db.orm_models.event_instance import EventInstanceORM
from app.adapters.db.orm_models.export_token import ExportTokenORM
from app.adapters.db.orm_models.invitation import CongregationInvitationORM
from app.adapters.db.orm_models.invitation_overwrite_request import (
    InvitationOverwriteRequestORM,
)
from app.adapters.db.orm_models.leader import LeaderORM
from app.adapters.db.orm_models.leader_registration import LeaderRegistrationORM
from app.adapters.db.orm_models.membership import MembershipORM
from app.adapters.db.orm_models.planning_series import PlanningSeriesORM
from app.adapters.db.orm_models.planning_slot import PlanningSlotORM
from app.adapters.db.orm_models.service_assignment import ServiceAssignmentORM
from app.adapters.db.orm_models.user import UserORM
