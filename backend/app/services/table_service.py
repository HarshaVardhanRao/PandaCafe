"""
Table management service layer.
Handles table operations, status updates, and table merging/splitting.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import Table, Order


class TableService:
    """Service for managing tables."""

    @staticmethod
    def create_table(
        db: Session,
        table_number: int,
        capacity: int,
        location: Optional[str] = None,
    ) -> Table:
        """
        Create new table.

        Args:
            db: Database session
            table_number: Table number/identifier
            capacity: Seating capacity
            location: Physical location description

        Returns:
            Created Table object
        """
        # Check if table number already exists
        existing = db.query(Table).filter(Table.table_number == table_number).first()
        if existing:
            raise ValueError(f"Table {table_number} already exists")

        table = Table(
            id=uuid.uuid4(),
            table_number=table_number,
            capacity=capacity,
            location=location,
            status="available",
        )

        db.add(table)
        db.commit()
        db.refresh(table)
        return table

    @staticmethod
    def get_table(db: Session, table_id: str) -> Optional[Table]:
        """Get table by ID."""
        return db.query(Table).filter(Table.id == table_id).first()

    @staticmethod
    def get_table_by_number(db: Session, table_number: int) -> Optional[Table]:
        """Get table by table number."""
        return db.query(Table).filter(Table.table_number == table_number).first()

    @staticmethod
    def list_tables(
        db: Session,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[Table], int]:
        """
        List tables with optional status filter.

        Returns:
            Tuple of (tables list, total count)
        """
        query = db.query(Table).filter(Table.deleted_at.is_(None))

        if status:
            query = query.filter(Table.status == status)

        total = query.count()
        tables = query.order_by(Table.table_number).limit(limit).offset(offset).all()

        return tables, total

    @staticmethod
    def update_table_status(db: Session, table_id: str, status: str) -> Table:
        """
        Update table status.

        Args:
            db: Database session
            table_id: Table ID
            status: New status (available, occupied, reserved, cleaning)

        Returns:
            Updated Table object
        """
        valid_statuses = ["available", "occupied", "reserved", "cleaning"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of {valid_statuses}")

        table = TableService.get_table(db, table_id)
        if not table:
            raise ValueError(f"Table {table_id} not found")

        table.status = status
        table.updated_at = datetime.utcnow()
        db.add(table)
        db.commit()
        db.refresh(table)
        return table

    @staticmethod
    def link_order_to_table(db: Session, table_id: str, order_id: str) -> Table:
        """Link order to table."""
        table = TableService.get_table(db, table_id)
        if not table:
            raise ValueError(f"Table {table_id} not found")

        table.current_order_id = order_id
        table.status = "occupied"
        table.updated_at = datetime.utcnow()
        db.add(table)
        db.commit()
        db.refresh(table)
        return table

    @staticmethod
    def unlink_order_from_table(db: Session, table_id: str) -> Table:
        """Unlink order from table."""
        table = TableService.get_table(db, table_id)
        if not table:
            raise ValueError(f"Table {table_id} not found")

        table.current_order_id = None
        table.status = "available"
        table.updated_at = datetime.utcnow()
        db.add(table)
        db.commit()
        db.refresh(table)
        return table

    @staticmethod
    def get_available_tables(db: Session, min_capacity: Optional[int] = None) -> List[Table]:
        """Get available tables, optionally filtered by capacity."""
        query = db.query(Table).filter(
            Table.status == "available",
            Table.deleted_at.is_(None),
        )

        if min_capacity:
            query = query.filter(Table.capacity >= min_capacity)

        return query.order_by(Table.table_number).all()

    @staticmethod
    def get_occupied_tables(db: Session) -> List[Table]:
        """Get all occupied tables."""
        return db.query(Table).filter(
            Table.status == "occupied",
            Table.deleted_at.is_(None),
        ).order_by(Table.table_number).all()

    @staticmethod
    def merge_tables(
        db: Session,
        table_ids: List[str],
        new_table_number: Optional[int] = None,
    ) -> Table:
        """
        Merge multiple tables into one.

        Args:
            db: Database session
            table_ids: List of table IDs to merge
            new_table_number: Optional new table number

        Returns:
            Merged Table object
        """
        if len(table_ids) < 2:
            raise ValueError("Must provide at least 2 tables to merge")

        tables = [TableService.get_table(db, tid) for tid in table_ids]

        if any(t is None for t in tables):
            raise ValueError("One or more tables not found")

        # Calculate new capacity
        new_capacity = sum(t.capacity for t in tables)

        # Create merged table or update first table
        primary_table = tables[0]
        primary_table.capacity = new_capacity

        if new_table_number:
            primary_table.table_number = new_table_number

        primary_table.updated_at = datetime.utcnow()
        db.add(primary_table)

        # Mark other tables as deleted
        for table in tables[1:]:
            table.deleted_at = datetime.utcnow()
            db.add(table)

        db.commit()
        db.refresh(primary_table)

        return primary_table

    @staticmethod
    def split_table(
        db: Session,
        table_id: str,
        new_capacity_1: int,
        new_capacity_2: int,
    ) -> tuple[Table, Table]:
        """
        Split table into two separate tables.

        Args:
            db: Database session
            table_id: Table ID to split
            new_capacity_1: Capacity for first table
            new_capacity_2: Capacity for second table

        Returns:
            Tuple of (table1, table2)
        """
        table = TableService.get_table(db, table_id)
        if not table:
            raise ValueError(f"Table {table_id} not found")

        total_capacity = new_capacity_1 + new_capacity_2

        if total_capacity > table.capacity:
            raise ValueError(
                f"Combined capacity ({total_capacity}) exceeds original ({table.capacity})"
            )

        # Update original table
        table.capacity = new_capacity_1
        table.updated_at = datetime.utcnow()
        db.add(table)

        # Create new table
        new_table = Table(
            id=uuid.uuid4(),
            table_number=TableService._get_next_table_number(db),
            capacity=new_capacity_2,
            location=table.location,
            status=table.status,
        )

        db.add(new_table)
        db.commit()

        db.refresh(table)
        db.refresh(new_table)

        return table, new_table

    @staticmethod
    def soft_delete_table(db: Session, table_id: str) -> None:
        """Soft delete table."""
        table = TableService.get_table(db, table_id)
        if not table:
            raise ValueError(f"Table {table_id} not found")

        table.deleted_at = datetime.utcnow()
        db.add(table)
        db.commit()

    @staticmethod
    def get_table_occupancy_report(db: Session) -> dict:
        """Get table occupancy statistics."""
        total = db.query(Table).filter(Table.deleted_at.is_(None)).count()
        available = db.query(Table).filter(
            Table.status == "available",
            Table.deleted_at.is_(None),
        ).count()
        occupied = db.query(Table).filter(
            Table.status == "occupied",
            Table.deleted_at.is_(None),
        ).count()
        reserved = db.query(Table).filter(
            Table.status == "reserved",
            Table.deleted_at.is_(None),
        ).count()
        cleaning = db.query(Table).filter(
            Table.status == "cleaning",
            Table.deleted_at.is_(None),
        ).count()

        return {
            "total_tables": total,
            "available": available,
            "occupied": occupied,
            "reserved": reserved,
            "cleaning": cleaning,
            "occupancy_rate": float(occupied / total * 100) if total > 0 else 0,
        }

    @staticmethod
    def _get_next_table_number(db: Session) -> int:
        """Get next available table number."""
        last_table = db.query(Table).order_by(Table.table_number.desc()).first()
        return (last_table.table_number if last_table else 0) + 1
