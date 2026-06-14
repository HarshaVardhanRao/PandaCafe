"""
Pydantic schemas for Reports & Analytics (Phase 6).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field


class PaymentMethodSummary(BaseModel):
    count: int
    total: Decimal


class DailyReportResponse(BaseModel):
    date: date
    total_sales: Decimal
    net_revenue: Decimal
    order_count: int
    average_order_value: Decimal
    tax_collected: Decimal
    discounts_given: Decimal
    orders_by_status: Dict[str, int]
    payments_by_method: Dict[str, PaymentMethodSummary]

    class Config:
        from_attributes = True


class TrendDataPoint(BaseModel):
    date: str  # YYYY-MM-DD format
    sales_amount: Decimal
    order_count: int


class TrendReportResponse(BaseModel):
    start_date: date
    end_date: date
    trends: List[TrendDataPoint]


class ProductPerformance(BaseModel):
    product_id: UUID
    sku: str
    name: str
    quantity_sold: int
    total_revenue: Decimal
    is_unsold: bool = False


class ProductReportResponse(BaseModel):
    start_date: date
    end_date: date
    top_products: List[ProductPerformance]
    least_selling_products: List[ProductPerformance]


class InventoryStockLevel(BaseModel):
    item_id: UUID
    item_name: str
    unit: str
    current_quantity: Decimal
    reorder_level: Decimal
    is_low_stock: bool
    product_name: Optional[str] = None


class InventoryMovement(BaseModel):
    item_id: UUID
    item_name: str
    unit: str
    transaction_type: str
    total_quantity: Decimal
    transaction_count: int


class InventoryReportResponse(BaseModel):
    stock_levels: List[InventoryStockLevel]
    movements: List[InventoryMovement]


class CashierPerformance(BaseModel):
    cashier_id: UUID
    username: str
    full_name: str
    orders_processed: int
    total_sales: Decimal
    average_order_value: Decimal


class ShiftSummaryResponse(BaseModel):
    shift_id: UUID
    cashier_name: str
    shift_date: date
    opening_cash: Decimal
    expected_cash: Optional[Decimal] = None
    actual_cash: Optional[Decimal] = None
    cash_difference: Optional[Decimal] = None
    status: str


class EmployeeReportResponse(BaseModel):
    start_date: date
    end_date: date
    cashier_performance: List[CashierPerformance]
    shift_summaries: List[ShiftSummaryResponse]
