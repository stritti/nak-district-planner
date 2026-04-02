import uuid
from datetime import datetime, timezone
import pytest
from app.domain.models.event import Event


@pytest.mark.parametrize(
    "title, expected_category",
    [
        ("Gottesdienst", "Gottesdienst"),
        ("Entschlafenengottesdienst", "Gottesdienst"),
        ("Festgottesdienst", "Gottesdienst"),
        ("Gottesdienst mit Taufe", "Gottesdienst"),
        ("Chorprobe", None),
        ("Jugendstunde", None),
    ],
)
def test_event_create_auto_categorization(title, expected_category):
    district_id = uuid.uuid4()
    event = Event.create(
        title=title,
        start_at=datetime.now(timezone.utc),
        end_at=datetime.now(timezone.utc),
        district_id=district_id,
    )
    assert event.category == expected_category


def test_event_apply_auto_categorization():
    district_id = uuid.uuid4()
    # Explicitly create with different category but keyword in title
    event = Event.create(
        title="Ein Festgottesdienst",
        start_at=datetime.now(timezone.utc),
        end_at=datetime.now(timezone.utc),
        district_id=district_id,
        category="Anderes",
    )
    # The logic in Event.create currently overrides category if keyword is found
    assert event.category == "Gottesdienst"

    # Test manual re-application
    event.title = "Nachtgebet"
    event.category = "Andacht"
    event.apply_auto_categorization()
    assert event.category == "Andacht"  # No change

    event.title = "Jugendgottesdienst"
    event.apply_auto_categorization()
    assert event.category == "Gottesdienst"
