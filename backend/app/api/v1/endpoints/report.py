"""
API router endpoints for Reports & Analytics (Phase 6).
"""

import io
import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import User, Role
from app.api.v1.endpoints.inventory import get_current_user
from app.services.report_service import ReportService
from app.schemas.report import (
    DailyReportResponse,
    TrendReportResponse,
    ProductReportResponse,
    InventoryReportResponse,
    EmployeeReportResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])


def check_report_access(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    """Restricts access to reports to users with Owner or Manager roles."""
    role = db.query(Role).filter(Role.id == current_user.role_id).first()
    role_name = role.name.lower() if role else ""
    if role_name not in ["owner", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Owner or Manager privileges required."
        )
    return current_user


@router.get("/daily", response_model=DailyReportResponse)
def get_daily_report(
    target_date: Optional[date] = Query(None),
    timezone: str = Query("UTC"),
    db: Session = Depends(get_db),
    user: User = Depends(check_report_access),
):
    """Retrieve operational and financial daily summary metrics."""
    if not target_date:
        target_date = date.today()
    try:
        return ReportService.get_daily_report(db, target_date, timezone)
    except Exception as e:
        logger.error(f"Error fetching daily report: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error compilation failed")


@router.get("/trends", response_model=TrendReportResponse)
def get_trends_report(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    timezone: str = Query("UTC"),
    db: Session = Depends(get_db),
    user: User = Depends(check_report_access),
):
    """Retrieve daily sales and order trends over a range of calendar days."""
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()
    try:
        return ReportService.get_trends_report(db, start_date, end_date, timezone)
    except Exception as e:
        logger.error(f"Error compiling trends report: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error trend compilation failed")


@router.get("/products", response_model=ProductReportResponse)
def get_products_report(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    timezone: str = Query("UTC"),
    db: Session = Depends(get_db),
    user: User = Depends(check_report_access),
):
    """Summarize product performance and identify top/least selling items."""
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()
    try:
        return ReportService.get_products_report(db, start_date, end_date, timezone)
    except Exception as e:
        logger.error(f"Error compiling products report: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error product compilation failed")


@router.get("/inventory", response_model=InventoryReportResponse)
def get_inventory_report(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    timezone: str = Query("UTC"),
    db: Session = Depends(get_db),
    user: User = Depends(check_report_access),
):
    """Retrieve current ingredient stock levels and movements."""
    try:
        return ReportService.get_inventory_report(db, start_date, end_date, timezone)
    except Exception as e:
        logger.error(f"Error compiling inventory report: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error inventory compilation failed")


@router.get("/employees", response_model=EmployeeReportResponse)
def get_employees_report(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    timezone: str = Query("UTC"),
    db: Session = Depends(get_db),
    user: User = Depends(check_report_access),
):
    """Retrieve cashier sales summaries and shift reconciliation logs."""
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()
    try:
        return ReportService.get_employees_report(db, start_date, end_date, timezone)
    except Exception as e:
        logger.error(f"Error compiling employees report: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error employee compilation failed")


@router.get("/{report_type}/export")
def export_report(
    report_type: str,
    format: str = Query("csv"),
    target_date: Optional[date] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    timezone: str = Query("UTC"),
    db: Session = Depends(get_db),
    user: User = Depends(check_report_access),
):
    """Export the requested report type in either CSV or PDF format."""
    report_type = report_type.lower()
    if report_type not in ["daily", "trends", "products", "inventory", "employees"]:
        raise HTTPException(status_code=400, detail="Invalid report type requested")

    format = format.lower()
    if format not in ["csv", "pdf"]:
        raise HTTPException(status_code=400, detail="Invalid format. Only csv or pdf are supported.")

    # 1. Compile Report Data
    if report_type == "daily":
        if not target_date:
            target_date = date.today()
        data = ReportService.get_daily_report(db, target_date, timezone)
    elif report_type == "trends":
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        data = ReportService.get_trends_report(db, start_date, end_date, timezone)
    elif report_type == "products":
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        data = ReportService.get_products_report(db, start_date, end_date, timezone)
    elif report_type == "inventory":
        data = ReportService.get_inventory_report(db, start_date, end_date, timezone)
    elif report_type == "employees":
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        data = ReportService.get_employees_report(db, start_date, end_date, timezone)

    # 2. Format and Stream Output
    if format == "csv":
        csv_string = ReportService.generate_csv_report(data, report_type)
        csv_bytes = csv_string.encode("utf-8")
        filename = f"{report_type}_report_{date.today().strftime('%Y%m%d')}.csv"
        return StreamingResponse(
            io.BytesIO(csv_bytes),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    elif format == "pdf":
        pdf_bytes = ReportService.generate_pdf_report(data, report_type)
        filename = f"{report_type}_report_{date.today().strftime('%Y%m%d')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
