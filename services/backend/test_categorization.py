import uuid
from datetime import datetime, timezone
from app.domain.models.event import Event


def test_auto_categorization():
    district_id = uuid.uuid4()

    test_cases = [
        ("Gottesdienst", "Gottesdienst"),
        ("Entschlafenengottesdienst", "Gottesdienst"),
        ("Festgottesdienst", "Gottesdienst"),
        ("Gottesdienst mit Taufe", "Gottesdienst"),
        ("Chorprobe", None),
        ("Jugendstunde", None),
    ]

    for title, expected_category in test_cases:
        event = Event.create(
            title=title,
            start_at=datetime.now(timezone.utc),
            end_at=datetime.now(timezone.utc),
            district_id=district_id,
        )
        print(
            f"Title: {title:25} | Category: {str(event.category):15} | Success: {event.category == expected_category}"
        )


if __name__ == "__main__":
    test_auto_categorization()
