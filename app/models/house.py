from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class House(Base):
    __tablename__ = "houses"

    houseid = Column(Integer, primary_key=True, index=True, autoincrement=True)
    apartment_block_num = Column(String(50, collation="NOCASE"), nullable=False, index=True)
    house_num = Column(String(50), nullable=False, index=True)

    # Relationships
    users = relationship("User", back_populates="house", cascade="all, delete-orphan")
    maintenance_requests = relationship("Maintenance", back_populates="house", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<House(houseid={self.houseid}, block='{self.apartment_block_num}', num='{self.house_num}')>"
