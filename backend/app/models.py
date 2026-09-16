from sqlalchemy import Integer, String, ForeignKey, Index, text, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Spot(Base):
    __tablename__ = 'spots'
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(12), unique=True)


class Stay(Base):
    __tablename__ = 'stays'
    id: Mapped[int] = mapped_column(primary_key=True)
    plate: Mapped[str] = mapped_column(String(7))
    vehicle: Mapped[str] = mapped_column(String(60), default='')
    spot_id: Mapped[int] = mapped_column(ForeignKey('spots.id'))
    entered_at: Mapped[int] = mapped_column(Integer)
    exited_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_hour: Mapped[int] = mapped_column(Integer)
    extra_hour: Mapped[int] = mapped_column(Integer)
    grace_minutes: Mapped[int] = mapped_column(Integer)
    amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    __table_args__ = (
        Index('one_active_plate', 'plate', unique=True,
              sqlite_where=text('exited_at IS NULL'), postgresql_where=text('exited_at IS NULL')),
        Index('one_active_spot', 'spot_id', unique=True,
              sqlite_where=text('exited_at IS NULL'), postgresql_where=text('exited_at IS NULL')),
        CheckConstraint('exited_at IS NULL OR exited_at >= entered_at'),
        CheckConstraint('amount_cents IS NULL OR amount_cents >= 0'),
    )
