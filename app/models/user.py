from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    userid = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    pw_hashed = Column(String(255), nullable=False)
    houseid = Column(Integer, ForeignKey("houses.houseid", ondelete="SET NULL"), nullable=True)
    isAdmin = Column(Boolean, default=False, nullable=False)

    # Relationships
    house = relationship("House", back_populates="users")
    maintenance_requests = relationship("Maintenance", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(userid={self.userid}, username='{self.username}', isAdmin={self.isAdmin}, houseid={self.houseid})>"
