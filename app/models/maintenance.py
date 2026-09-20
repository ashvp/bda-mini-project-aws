from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class Maintenance(Base):
    __tablename__ = "maintanance"

    maintanance_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    date = Column(DateTime, default=get_utc_now, nullable=False)
    houseid = Column(Integer, ForeignKey("houses.houseid", ondelete="CASCADE"), nullable=False)
    userid = Column(Integer, ForeignKey("users.userid", ondelete="CASCADE"), nullable=False)
    problem_category = Column(String(100), nullable=False, index=True)
    details = Column(Text, nullable=False)
    image_url = Column(String(1024), nullable=False)
    isAssignedTo = Column(String(150), nullable=True, default=None)

    # Relationships
    house = relationship("House", back_populates="maintenance_requests")
    user = relationship("User", back_populates="maintenance_requests")

    def __repr__(self) -> str:
        return (
            f"<Maintenance(id={self.maintanance_id}, category='{self.problem_category}', "
            f"user_id={self.userid}, house_id={self.houseid}, isAssignedTo='{self.isAssignedTo}')>"
        )
