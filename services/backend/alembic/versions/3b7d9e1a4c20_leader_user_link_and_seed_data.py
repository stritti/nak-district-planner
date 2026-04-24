"""Link leaders to users and seed base demo data.

Revision ID: 3b7d9e1a4c20
Revises: 2a9c4d5e6f70
Create Date: 2026-04-03 13:45:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "3b7d9e1a4c20"
down_revision: str | None = "2a9c4d5e6f70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("leaders", sa.Column("user_sub", sa.String(length=512), nullable=True))
    op.create_index("ix_leaders_user_sub", "leaders", ["user_sub"], unique=False)
    op.create_foreign_key(
        "fk_leaders_user_sub",
        "leaders",
        "users",
        ["user_sub"],
        ["sub"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        INSERT INTO districts (id, name, state_code, created_at, updated_at)
        VALUES
          ('5fd81892-cb13-4d98-8b38-9448cf610d09', 'Bezirk Stuttgart-Mitte', 'BW', now(), now()),
          ('f5c273f9-4f26-4f4e-a7d4-a8f20f0cbf13', 'Bezirk Frankfurt', 'HE', now(), now()),
          ('98bf6ef6-c61f-4d35-9f6f-0f88a4374a34', 'Bezirk Hamburg', 'HH', now(), now())
        ON CONFLICT (id) DO UPDATE
        SET
          name = EXCLUDED.name,
          state_code = EXCLUDED.state_code,
          updated_at = now();
        """
    )

    op.execute(
        r"""
        INSERT INTO congregations (id, name, district_id, created_at, updated_at, service_times)
        VALUES
          ('5a8fcd84-1576-4f8f-b4f0-3028e25031a7', 'Stuttgart-Nord', '5fd81892-cb13-4d98-8b38-9448cf610d09', now(), now(), $$[{"weekday"\:6,"time":"09\:30"},{"weekday"\:2,"time":"20\:00"}]$$::jsonb),
          ('9f2d3841-f255-4846-bf6a-f45050ee9ed8', 'Stuttgart-West', '5fd81892-cb13-4d98-8b38-9448cf610d09', now(), now(), $$[{"weekday"\:6,"time":"09\:30"},{"weekday"\:2,"time":"20\:00"}]$$::jsonb),
          ('d6880cc0-a4bb-405f-abcb-ea46a526a889', 'Ludwigsburg', '5fd81892-cb13-4d98-8b38-9448cf610d09', now(), now(), $$[{"weekday"\:6,"time":"09\:30"},{"weekday"\:2,"time":"20\:00"}]$$::jsonb),
          ('e2272b8a-6012-4da2-a900-1ec02b7b5033', 'Frankfurt-Innenstadt', 'f5c273f9-4f26-4f4e-a7d4-a8f20f0cbf13', now(), now(), $$[{"weekday"\:6,"time":"09\:30"},{"weekday"\:2,"time":"20\:00"}]$$::jsonb),
          ('45f57429-f91e-41fd-a87f-fafe6b9d1a57', 'Offenbach', 'f5c273f9-4f26-4f4e-a7d4-a8f20f0cbf13', now(), now(), $$[{"weekday"\:6,"time":"09\:30"},{"weekday"\:2,"time":"20\:00"}]$$::jsonb),
          ('374f68e5-b8cf-4e30-9c7d-8f24e16abdae', 'Bad Homburg', 'f5c273f9-4f26-4f4e-a7d4-a8f20f0cbf13', now(), now(), $$[{"weekday"\:6,"time":"09\:30"},{"weekday"\:2,"time":"20\:00"}]$$::jsonb),
          ('f85e6964-86fd-4616-9850-8c0ca772bf39', 'Hamburg-Mitte', '98bf6ef6-c61f-4d35-9f6f-0f88a4374a34', now(), now(), $$[{"weekday"\:6,"time":"09\:30"},{"weekday"\:2,"time":"20\:00"}]$$::jsonb),
          ('4f658379-1d6c-40c9-82b8-c80472d6864f', 'Hamburg-Altona', '98bf6ef6-c61f-4d35-9f6f-0f88a4374a34', now(), now(), $$[{"weekday"\:6,"time":"09\:30"},{"weekday"\:2,"time":"20\:00"}]$$::jsonb),
          ('95c721cb-e58a-4979-b92b-faacd032bd39', 'Norderstedt', '98bf6ef6-c61f-4d35-9f6f-0f88a4374a34', now(), now(), $$[{"weekday"\:6,"time":"09\:30"},{"weekday"\:2,"time":"20\:00"}]$$::jsonb)
        ON CONFLICT (id) DO UPDATE
        SET
          name = EXCLUDED.name,
          district_id = EXCLUDED.district_id,
          service_times = EXCLUDED.service_times,
          updated_at = now();
        """
    )

    op.execute(
        """
        INSERT INTO leaders (
          id, name, district_id, congregation_id, rank, special_role, user_sub,
          email, phone, notes, is_active, created_at, updated_at
        )
        VALUES
          ('d6ef9496-c044-4a3a-8622-b563de46db9f', 'Markus Weber', '5fd81892-cb13-4d98-8b38-9448cf610d09', NULL, 'BÄ', 'Bezirksvorsteher', NULL, NULL, NULL, NULL, true, now(), now()),
          ('8f8f5235-83fd-470d-8fbe-7a3f6085b380', 'Daniel Hoffmann', '5fd81892-cb13-4d98-8b38-9448cf610d09', '5a8fcd84-1576-4f8f-b4f0-3028e25031a7', 'Pr.', 'Gemeindevorsteher', NULL, NULL, NULL, NULL, true, now(), now()),
          ('6e3e87b4-7c52-48df-8b43-7edcf0eeef9e', 'Tobias Schenk', '5fd81892-cb13-4d98-8b38-9448cf610d09', '9f2d3841-f255-4846-bf6a-f45050ee9ed8', 'Pr.', 'Gemeindevorsteher', NULL, NULL, NULL, NULL, true, now(), now()),
          ('e507b3bb-8afd-4f4e-aa82-f7e44f266f16', 'Stefan Bauer', '5fd81892-cb13-4d98-8b38-9448cf610d09', 'd6880cc0-a4bb-405f-abcb-ea46a526a889', 'Ev.', NULL, NULL, NULL, NULL, NULL, true, now(), now()),
          ('f825a0c5-98dc-42ba-ad4f-51f943f30d4f', 'Johannes Keller', 'f5c273f9-4f26-4f4e-a7d4-a8f20f0cbf13', NULL, 'BE', 'Bezirksvorsteher', NULL, NULL, NULL, NULL, true, now(), now()),
          ('95302665-6f64-4048-ba59-a5a591ea2448', 'Benjamin Roth', 'f5c273f9-4f26-4f4e-a7d4-a8f20f0cbf13', 'e2272b8a-6012-4da2-a900-1ec02b7b5033', 'Pr.', 'Gemeindevorsteher', NULL, NULL, NULL, NULL, true, now(), now()),
          ('1e0d6e3f-a4b4-46ba-a60d-4f57d318b625', 'Michael Hartmann', 'f5c273f9-4f26-4f4e-a7d4-a8f20f0cbf13', '45f57429-f91e-41fd-a87f-fafe6b9d1a57', 'Pr.', NULL, NULL, NULL, NULL, NULL, true, now(), now()),
          ('6d186e60-89d1-4f9e-bfba-51bc7ed4dfea', 'Lukas Neumann', 'f5c273f9-4f26-4f4e-a7d4-a8f20f0cbf13', '374f68e5-b8cf-4e30-9c7d-8f24e16abdae', 'Di.', NULL, NULL, NULL, NULL, NULL, true, now(), now()),
          ('a5d92117-8b69-4719-b5af-e1e8a43e0f0d', 'Andreas Vogel', '98bf6ef6-c61f-4d35-9f6f-0f88a4374a34', NULL, 'Hi.', 'Bezirksvorsteher', NULL, NULL, NULL, NULL, true, now(), now()),
          ('f6a9971e-d487-4cb4-9a85-94cb62b2e8ec', 'Sebastian Krause', '98bf6ef6-c61f-4d35-9f6f-0f88a4374a34', 'f85e6964-86fd-4616-9850-8c0ca772bf39', 'Pr.', 'Gemeindevorsteher', NULL, NULL, NULL, NULL, true, now(), now()),
          ('20ab1d71-e48f-40e3-a2d2-d0cd0bca247c', 'Patrick Schmitt', '98bf6ef6-c61f-4d35-9f6f-0f88a4374a34', '4f658379-1d6c-40c9-82b8-c80472d6864f', 'Ev.', NULL, NULL, NULL, NULL, NULL, true, now(), now()),
          ('04cb7e7a-9b5c-4e68-9f75-25fdaf4cc8f1', 'Florian Schulz', '98bf6ef6-c61f-4d35-9f6f-0f88a4374a34', '95c721cb-e58a-4979-b92b-faacd032bd39', 'Di.', NULL, NULL, NULL, NULL, NULL, true, now(), now())
        ON CONFLICT (id) DO UPDATE
        SET
          name = EXCLUDED.name,
          district_id = EXCLUDED.district_id,
          congregation_id = EXCLUDED.congregation_id,
          rank = EXCLUDED.rank,
          special_role = EXCLUDED.special_role,
          is_active = EXCLUDED.is_active,
          updated_at = now();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM leaders
        WHERE id IN (
          'd6ef9496-c044-4a3a-8622-b563de46db9f', '8f8f5235-83fd-470d-8fbe-7a3f6085b380',
          '6e3e87b4-7c52-48df-8b43-7edcf0eeef9e', 'e507b3bb-8afd-4f4e-aa82-f7e44f266f16',
          'f825a0c5-98dc-42ba-ad4f-51f943f30d4f', '95302665-6f64-4048-ba59-a5a591ea2448',
          '1e0d6e3f-a4b4-46ba-a60d-4f57d318b625', '6d186e60-89d1-4f9e-bfba-51bc7ed4dfea',
          'a5d92117-8b69-4719-b5af-e1e8a43e0f0d', 'f6a9971e-d487-4cb4-9a85-94cb62b2e8ec',
          '20ab1d71-e48f-40e3-a2d2-d0cd0bca247c', '04cb7e7a-9b5c-4e68-9f75-25fdaf4cc8f1'
        );
        """
    )
    op.execute(
        """
        DELETE FROM congregations
        WHERE id IN (
          '5a8fcd84-1576-4f8f-b4f0-3028e25031a7', '9f2d3841-f255-4846-bf6a-f45050ee9ed8',
          'd6880cc0-a4bb-405f-abcb-ea46a526a889', 'e2272b8a-6012-4da2-a900-1ec02b7b5033',
          '45f57429-f91e-41fd-a87f-fafe6b9d1a57', '374f68e5-b8cf-4e30-9c7d-8f24e16abdae',
          'f85e6964-86fd-4616-9850-8c0ca772bf39', '4f658379-1d6c-40c9-82b8-c80472d6864f',
          '95c721cb-e58a-4979-b92b-faacd032bd39'
        );
        """
    )
    op.execute(
        """
        DELETE FROM districts
        WHERE id IN (
          '5fd81892-cb13-4d98-8b38-9448cf610d09',
          'f5c273f9-4f26-4f4e-a7d4-a8f20f0cbf13',
          '98bf6ef6-c61f-4d35-9f6f-0f88a4374a34'
        );
        """
    )

    op.drop_constraint("fk_leaders_user_sub", "leaders", type_="foreignkey")
    op.drop_index("ix_leaders_user_sub", table_name="leaders")
    op.drop_column("leaders", "user_sub")
