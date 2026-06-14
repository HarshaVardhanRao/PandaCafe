"""
Unit tests for table service (Phase 2).
Tests for table management, status updates, and table operations.
"""

import pytest
from sqlalchemy.orm import Session

from app.models import Table, Order, User
from app.schemas.order import OrderCreateRequest
from app.services.table_service import TableService
from app.services.order_service import OrderService


class TestTableCreation:
    """Tests for table creation."""

    def test_create_table(self, db: Session):
        """Test creating new table."""
        table = TableService.create_table(
            db,
            table_number=1,
            capacity=4,
            location="Window",
        )

        assert table.table_number == 1
        assert table.capacity == 4
        assert table.location == "Window"
        assert table.status == "available"

    def test_create_duplicate_table_number(self, db: Session):
        """Test creating table with duplicate number."""
        TableService.create_table(db, table_number=1, capacity=4)

        with pytest.raises(ValueError, match="already exists"):
            TableService.create_table(db, table_number=1, capacity=2)

    def test_create_table_no_location(self, db: Session):
        """Test creating table without location."""
        table = TableService.create_table(
            db,
            table_number=5,
            capacity=2,
        )

        assert table.location is None


class TestTableRetrieval:
    """Tests for table retrieval."""

    def test_get_table_by_id(self, db: Session):
        """Test getting table by ID."""
        created_table = TableService.create_table(db, table_number=1, capacity=4)

        retrieved_table = TableService.get_table(db, str(created_table.id))

        assert retrieved_table.id == created_table.id

    def test_get_table_by_number(self, db: Session):
        """Test getting table by table number."""
        TableService.create_table(db, table_number=5, capacity=4)

        table = TableService.get_table_by_number(db, 5)

        assert table.table_number == 5

    def test_get_nonexistent_table(self, db: Session):
        """Test getting nonexistent table."""
        table = TableService.get_table(db, "nonexistent-id")

        assert table is None

    def test_list_tables(self, db: Session):
        """Test listing tables."""
        for i in range(1, 4):
            TableService.create_table(db, table_number=i, capacity=4)

        tables, total = TableService.list_tables(db)

        assert total == 3
        assert len(tables) == 3

    def test_list_available_tables(self, db: Session):
        """Test filtering available tables."""
        table1 = TableService.create_table(db, table_number=1, capacity=4)
        table2 = TableService.create_table(db, table_number=2, capacity=4)

        # Mark one as occupied
        TableService.update_table_status(db, str(table2.id), "occupied")

        available_tables = TableService.get_available_tables(db)

        assert len(available_tables) == 1
        assert available_tables[0].id == table1.id


class TestTableStatus:
    """Tests for table status management."""

    def test_update_table_status(self, db: Session):
        """Test updating table status."""
        table = TableService.create_table(db, table_number=1, capacity=4)

        updated_table = TableService.update_table_status(db, str(table.id), "occupied")

        assert updated_table.status == "occupied"

    def test_update_to_reserved(self, db: Session):
        """Test updating table to reserved."""
        table = TableService.create_table(db, table_number=1, capacity=4)

        updated_table = TableService.update_table_status(db, str(table.id), "reserved")

        assert updated_table.status == "reserved"

    def test_update_to_cleaning(self, db: Session):
        """Test updating table to cleaning."""
        table = TableService.create_table(db, table_number=1, capacity=4)

        updated_table = TableService.update_table_status(db, str(table.id), "cleaning")

        assert updated_table.status == "cleaning"

    def test_invalid_status(self, db: Session):
        """Test setting invalid status."""
        table = TableService.create_table(db, table_number=1, capacity=4)

        with pytest.raises(ValueError, match="Invalid status"):
            TableService.update_table_status(db, str(table.id), "invalid")


class TestTableOrdering:
    """Tests for linking tables to orders."""

    def test_link_order_to_table(self, db: Session, test_user: User):
        """Test linking order to table."""
        table = TableService.create_table(db, table_number=1, capacity=4)

        order_request = OrderCreateRequest(order_type="dine_in", table_id=str(table.id))
        order = OrderService.create_order(db, order_request, str(test_user.id))

        linked_table = TableService.link_order_to_table(db, str(table.id), str(order.id))

        assert linked_table.current_order_id == order.id
        assert linked_table.status == "occupied"

    def test_unlink_order_from_table(self, db: Session, test_user: User):
        """Test unlinking order from table."""
        table = TableService.create_table(db, table_number=1, capacity=4)

        order_request = OrderCreateRequest(order_type="dine_in", table_id=str(table.id))
        order = OrderService.create_order(db, order_request, str(test_user.id))

        TableService.link_order_to_table(db, str(table.id), str(order.id))
        unlinked_table = TableService.unlink_order_from_table(db, str(table.id))

        assert unlinked_table.current_order_id is None
        assert unlinked_table.status == "available"


class TestTableMerging:
    """Tests for table merging."""

    def test_merge_two_tables(self, db: Session):
        """Test merging two tables."""
        table1 = TableService.create_table(db, table_number=1, capacity=4)
        table2 = TableService.create_table(db, table_number=2, capacity=2)

        merged_table = TableService.merge_tables(db, [str(table1.id), str(table2.id)])

        assert merged_table.capacity == 6  # 4 + 2

    def test_merge_three_tables(self, db: Session):
        """Test merging three tables."""
        table1 = TableService.create_table(db, table_number=1, capacity=2)
        table2 = TableService.create_table(db, table_number=2, capacity=2)
        table3 = TableService.create_table(db, table_number=3, capacity=4)

        merged_table = TableService.merge_tables(
            db,
            [str(table1.id), str(table2.id), str(table3.id)],
        )

        assert merged_table.capacity == 8  # 2 + 2 + 4

    def test_merge_with_single_table(self, db: Session):
        """Test merging with single table fails."""
        table = TableService.create_table(db, table_number=1, capacity=4)

        with pytest.raises(ValueError, match="at least 2"):
            TableService.merge_tables(db, [str(table.id)])

    def test_merge_with_new_number(self, db: Session):
        """Test merging tables with new table number."""
        table1 = TableService.create_table(db, table_number=1, capacity=4)
        table2 = TableService.create_table(db, table_number=2, capacity=2)

        merged_table = TableService.merge_tables(
            db,
            [str(table1.id), str(table2.id)],
            new_table_number=10,
        )

        assert merged_table.table_number == 10


class TestTableSplitting:
    """Tests for table splitting."""

    def test_split_table(self, db: Session):
        """Test splitting table."""
        original_table = TableService.create_table(db, table_number=1, capacity=6)

        table1, table2 = TableService.split_table(
            db,
            str(original_table.id),
            new_capacity_1=4,
            new_capacity_2=2,
        )

        assert table1.capacity == 4
        assert table2.capacity == 2

    def test_split_exceeds_capacity(self, db: Session):
        """Test splitting with combined capacity exceeding original."""
        table = TableService.create_table(db, table_number=1, capacity=4)

        with pytest.raises(ValueError, match="exceeds original"):
            TableService.split_table(db, str(table.id), 3, 3)

    def test_split_equal_parts(self, db: Session):
        """Test splitting table into equal parts."""
        original_table = TableService.create_table(db, table_number=1, capacity=4)

        table1, table2 = TableService.split_table(
            db,
            str(original_table.id),
            new_capacity_1=2,
            new_capacity_2=2,
        )

        assert table1.capacity == 2
        assert table2.capacity == 2


class TestTableOccupancy:
    """Tests for table occupancy reporting."""

    def test_occupancy_report_all_available(self, db: Session):
        """Test occupancy report with all available tables."""
        for i in range(1, 4):
            TableService.create_table(db, table_number=i, capacity=4)

        report = TableService.get_table_occupancy_report(db)

        assert report["total_tables"] == 3
        assert report["available"] == 3
        assert report["occupied"] == 0
        assert report["occupancy_rate"] == 0.0

    def test_occupancy_report_mixed(self, db: Session):
        """Test occupancy report with mixed statuses."""
        table1 = TableService.create_table(db, table_number=1, capacity=4)
        table2 = TableService.create_table(db, table_number=2, capacity=4)
        table3 = TableService.create_table(db, table_number=3, capacity=4)

        # Update statuses
        TableService.update_table_status(db, str(table2.id), "occupied")
        TableService.update_table_status(db, str(table3.id), "reserved")

        report = TableService.get_table_occupancy_report(db)

        assert report["total_tables"] == 3
        assert report["available"] == 1
        assert report["occupied"] == 1
        assert report["reserved"] == 1
        assert report["occupancy_rate"] == 33.33333333333333

    def test_capacity_filtering(self, db: Session):
        """Test filtering available tables by capacity."""
        TableService.create_table(db, table_number=1, capacity=2)
        TableService.create_table(db, table_number=2, capacity=4)
        TableService.create_table(db, table_number=3, capacity=6)

        tables = TableService.get_available_tables(db, min_capacity=4)

        assert len(tables) == 2
        assert all(t.capacity >= 4 for t in tables)
