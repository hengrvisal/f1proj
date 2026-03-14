"""initial schema - 16 tables

Revision ID: 054a31680622
Revises: 
Create Date: 2026-03-13 20:21:24.056781

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '054a31680622'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("year", sa.Integer(), nullable=False, unique=True),
    )

    op.create_table(
        "circuits",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("circuit_ref", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255)),
        sa.Column("country", sa.String(100)),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("url", sa.Text()),
    )

    op.create_table(
        "constructors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("constructor_ref", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("nationality", sa.String(100)),
        sa.Column("url", sa.Text()),
    )

    op.create_table(
        "drivers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("driver_ref", sa.String(100), nullable=False, unique=True),
        sa.Column("code", sa.String(10)),
        sa.Column("permanent_number", sa.Integer()),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("date_of_birth", sa.Date()),
        sa.Column("nationality", sa.String(100)),
        sa.Column("url", sa.Text()),
    )

    op.create_table(
        "races",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id"), nullable=False),
        sa.Column("circuit_id", sa.Integer(), sa.ForeignKey("circuits.id"), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("date", sa.Date()),
        sa.Column("url", sa.Text()),
        sa.Column("openf1_meeting_key", sa.Integer()),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("race_id", sa.Integer(), sa.ForeignKey("races.id"), nullable=False),
        sa.Column("session_type", sa.String(20), nullable=False),
        sa.Column("date", sa.DateTime()),
        sa.Column("openf1_session_key", sa.Integer()),
    )

    op.create_table(
        "driver_race_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("race_id", sa.Integer(), sa.ForeignKey("races.id"), nullable=False),
        sa.Column("driver_id", sa.Integer(), sa.ForeignKey("drivers.id"), nullable=False),
        sa.Column("constructor_id", sa.Integer(), sa.ForeignKey("constructors.id"), nullable=False),
        sa.Column("driver_number", sa.Integer(), nullable=False),
        sa.UniqueConstraint("race_id", "driver_id", name="uq_driver_race_entry"),
    )

    op.create_table(
        "race_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("race_id", sa.Integer(), sa.ForeignKey("races.id"), nullable=False),
        sa.Column("driver_id", sa.Integer(), sa.ForeignKey("drivers.id"), nullable=False),
        sa.Column("constructor_id", sa.Integer(), sa.ForeignKey("constructors.id"), nullable=False),
        sa.Column("grid_position", sa.Integer()),
        sa.Column("finish_position", sa.Integer()),
        sa.Column("position_text", sa.String(10)),
        sa.Column("points", sa.Float()),
        sa.Column("laps_completed", sa.Integer()),
        sa.Column("status", sa.String(100)),
        sa.Column("time_ms", sa.Integer()),
        sa.Column("fastest_lap_time_ms", sa.Integer()),
        sa.Column("fastest_lap_number", sa.Integer()),
        sa.UniqueConstraint("race_id", "driver_id", name="uq_race_result"),
    )

    op.create_table(
        "qualifying_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("race_id", sa.Integer(), sa.ForeignKey("races.id"), nullable=False),
        sa.Column("driver_id", sa.Integer(), sa.ForeignKey("drivers.id"), nullable=False),
        sa.Column("constructor_id", sa.Integer(), sa.ForeignKey("constructors.id"), nullable=False),
        sa.Column("position", sa.Integer()),
        sa.Column("q1_ms", sa.Integer()),
        sa.Column("q2_ms", sa.Integer()),
        sa.Column("q3_ms", sa.Integer()),
        sa.UniqueConstraint("race_id", "driver_id", name="uq_qualifying_result"),
    )

    op.create_table(
        "laps",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("driver_id", sa.Integer(), sa.ForeignKey("drivers.id"), nullable=False),
        sa.Column("lap_number", sa.Integer(), nullable=False),
        sa.Column("lap_time_ms", sa.Integer()),
        sa.Column("sector1_ms", sa.Integer()),
        sa.Column("sector2_ms", sa.Integer()),
        sa.Column("sector3_ms", sa.Integer()),
        sa.Column("compound", sa.String(20)),
        sa.Column("tyre_life", sa.Integer()),
        sa.Column("is_pit_in_lap", sa.Boolean()),
        sa.Column("is_pit_out_lap", sa.Boolean()),
        sa.Column("is_personal_best", sa.Boolean()),
        sa.Column("position", sa.Integer()),
        sa.Column("speed_trap", sa.Float()),
        sa.UniqueConstraint("session_id", "driver_id", "lap_number", name="uq_lap"),
    )

    op.create_table(
        "pit_stops",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("race_id", sa.Integer(), sa.ForeignKey("races.id"), nullable=False),
        sa.Column("driver_id", sa.Integer(), sa.ForeignKey("drivers.id"), nullable=False),
        sa.Column("stop_number", sa.Integer(), nullable=False),
        sa.Column("lap_number", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("total_time_ms", sa.Integer()),
        sa.UniqueConstraint("race_id", "driver_id", "stop_number", name="uq_pit_stop"),
    )

    op.create_table(
        "tyre_stints",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("driver_id", sa.Integer(), sa.ForeignKey("drivers.id"), nullable=False),
        sa.Column("stint_number", sa.Integer(), nullable=False),
        sa.Column("compound", sa.String(20)),
        sa.Column("start_lap", sa.Integer()),
        sa.Column("end_lap", sa.Integer()),
        sa.Column("tyre_age_at_start", sa.Integer()),
        sa.UniqueConstraint("session_id", "driver_id", "stint_number", name="uq_tyre_stint"),
    )

    op.create_table(
        "weather",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("timestamp", sa.DateTime()),
        sa.Column("air_temp", sa.Float()),
        sa.Column("track_temp", sa.Float()),
        sa.Column("humidity", sa.Float()),
        sa.Column("pressure", sa.Float()),
        sa.Column("wind_speed", sa.Float()),
        sa.Column("wind_direction", sa.Integer()),
        sa.Column("rainfall", sa.Boolean()),
    )

    op.create_table(
        "telemetry_samples",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("driver_id", sa.Integer(), sa.ForeignKey("drivers.id"), nullable=False),
        sa.Column("lap_number", sa.Integer(), nullable=False),
        sa.Column("distance_m", sa.Integer(), nullable=False),
        sa.Column("speed", sa.Float()),
        sa.Column("throttle", sa.SmallInteger()),
        sa.Column("brake", sa.Boolean()),
        sa.Column("gear", sa.SmallInteger()),
        sa.Column("rpm", sa.Integer()),
        sa.Column("drs", sa.SmallInteger()),
        sa.Column("x", sa.Float()),
        sa.Column("y", sa.Float()),
        sa.UniqueConstraint(
            "session_id", "driver_id", "lap_number", "distance_m",
            name="uq_telemetry_sample",
        ),
    )

    op.create_table(
        "race_control_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("timestamp", sa.DateTime()),
        sa.Column("lap_number", sa.Integer()),
        sa.Column("category", sa.String(50)),
        sa.Column("flag", sa.String(50)),
        sa.Column("message", sa.Text()),
        sa.Column("driver_number", sa.Integer()),
    )

    op.create_table(
        "team_radio",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("driver_id", sa.Integer(), sa.ForeignKey("drivers.id"), nullable=False),
        sa.Column("timestamp", sa.DateTime()),
        sa.Column("recording_url", sa.Text()),
    )

    # Indexes for high-volume tables
    op.create_index("ix_laps_session_driver", "laps", ["session_id", "driver_id"])
    op.create_index("ix_telemetry_session_driver_lap", "telemetry_samples", ["session_id", "driver_id", "lap_number"])
    op.create_index("ix_weather_session", "weather", ["session_id"])
    op.create_index("ix_race_control_session", "race_control_messages", ["session_id"])


def downgrade() -> None:
    op.drop_table("team_radio")
    op.drop_table("race_control_messages")
    op.drop_table("telemetry_samples")
    op.drop_table("weather")
    op.drop_table("tyre_stints")
    op.drop_table("pit_stops")
    op.drop_table("laps")
    op.drop_table("qualifying_results")
    op.drop_table("race_results")
    op.drop_table("driver_race_entries")
    op.drop_table("sessions")
    op.drop_table("races")
    op.drop_table("drivers")
    op.drop_table("constructors")
    op.drop_table("circuits")
    op.drop_table("seasons")
