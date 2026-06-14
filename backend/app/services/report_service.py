"""
Business logic and formatting services for reports and analytics (Phase 6).
"""

import csv
import io
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from zoneinfo import ZoneInfo
from datetime import timezone as datetime_timezone
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    Order,
    OrderItem,
    Payment,
    InventoryItem,
    InventoryTransaction,
    Shift,
    User,
    Product,
)

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

logger = logging.getLogger(__name__)


class ReportService:
    """Service class for compiling and exporting operational and financial reports."""

    @staticmethod
    def get_date_bounds(target_date: date, tz_name: str = "UTC") -> tuple[datetime, datetime]:
        """Convert a local calendar date to UTC start and end datetime bounds."""
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo("UTC")

        local_start = datetime.combine(target_date, datetime.min.time(), tzinfo=tz)
        local_end = datetime.combine(target_date, datetime.max.time(), tzinfo=tz)

        # Convert to UTC (naive UTC as stored in the DB)
        utc_start = local_start.astimezone(datetime_timezone.utc).replace(tzinfo=None)
        utc_end = local_end.astimezone(datetime_timezone.utc).replace(tzinfo=None)

        return utc_start, utc_end

    @staticmethod
    def get_datetime_bounds(start_date: date, end_date: date, tz_name: str = "UTC") -> tuple[datetime, datetime]:
        """Convert a start and end calendar date to naive UTC datetime boundaries."""
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo("UTC")

        local_start = datetime.combine(start_date, datetime.min.time(), tzinfo=tz)
        local_end = datetime.combine(end_date, datetime.max.time(), tzinfo=tz)

        utc_start = local_start.astimezone(datetime_timezone.utc).replace(tzinfo=None)
        utc_end = local_end.astimezone(datetime_timezone.utc).replace(tzinfo=None)

        return utc_start, utc_end

    @classmethod
    def get_daily_report(cls, db: Session, target_date: date, tz_name: str = "UTC") -> Dict[str, Any]:
        """Compile daily sales, revenue, order, and payment metrics."""
        utc_start, utc_end = cls.get_date_bounds(target_date, tz_name)

        # 1. Fetch completed orders in date range
        orders = db.query(Order).filter(
            Order.status == "completed",
            Order.completed_at >= utc_start,
            Order.completed_at <= utc_end
        ).all()

        total_sales = sum((o.total_amount for o in orders), Decimal("0.00"))
        order_count = len(orders)
        average_order_value = total_sales / Decimal(order_count) if order_count > 0 else Decimal("0.00")
        tax_collected = sum((o.tax_amount for o in orders), Decimal("0.00"))
        discounts_given = sum((o.discount_amount for o in orders), Decimal("0.00"))

        # 2. Fetch completed payments in date range for net revenue calculation
        payments = db.query(Payment).filter(
            Payment.payment_status == "completed",
            Payment.created_at >= utc_start,
            Payment.created_at <= utc_end
        ).all()
        net_revenue = sum((p.amount for p in payments), Decimal("0.00"))

        # 3. Orders by Status (orders created on this date)
        status_counts = db.query(
            Order.status, func.count(Order.id)
        ).filter(
            Order.created_at >= utc_start,
            Order.created_at <= utc_end
        ).group_by(Order.status).all()

        # Initialize with standard statuses
        orders_by_status = {
            "pending": 0,
            "accepted": 0,
            "preparing": 0,
            "ready": 0,
            "served": 0,
            "completed": 0,
            "cancelled": 0,
        }
        for s, count in status_counts:
            orders_by_status[s] = count

        # 4. Payments by Method
        payment_methods = ["cash", "upi", "card", "split"]
        payments_by_method = {
            m: {"count": 0, "total": Decimal("0.00")} for m in payment_methods
        }
        for p in payments:
            method = p.payment_method.lower()
            if method not in payments_by_method:
                payments_by_method[method] = {"count": 0, "total": Decimal("0.00")}
            payments_by_method[method]["count"] += 1
            payments_by_method[method]["total"] += p.amount

        return {
            "date": target_date,
            "total_sales": total_sales,
            "net_revenue": net_revenue,
            "order_count": order_count,
            "average_order_value": average_order_value,
            "tax_collected": tax_collected,
            "discounts_given": discounts_given,
            "orders_by_status": orders_by_status,
            "payments_by_method": payments_by_method,
        }

    @classmethod
    def get_trends_report(cls, db: Session, start_date: date, end_date: date, tz_name: str = "UTC") -> Dict[str, Any]:
        """Aggregate sales and order trends over a date range."""
        trends = []
        current = start_date
        while current <= end_date:
            utc_start, utc_end = cls.get_date_bounds(current, tz_name)

            orders_aggregate = db.query(
                func.sum(Order.total_amount).label("sales"),
                func.count(Order.id).label("count")
            ).filter(
                Order.status == "completed",
                Order.completed_at >= utc_start,
                Order.completed_at <= utc_end
            ).first()

            sales_amt = orders_aggregate.sales if orders_aggregate.sales is not None else Decimal("0.00")
            order_count = orders_aggregate.count if orders_aggregate.count is not None else 0

            trends.append({
                "date": current.strftime("%Y-%m-%d"),
                "sales_amount": Decimal(sales_amt),
                "order_count": int(order_count)
            })
            current += timedelta(days=1)

        return {
            "start_date": start_date,
            "end_date": end_date,
            "trends": trends
        }

    @classmethod
    def get_products_report(cls, db: Session, start_date: date, end_date: date, tz_name: str = "UTC") -> Dict[str, Any]:
        """Summarize product performance sales and classify top/least sellers."""
        utc_start, utc_end = cls.get_datetime_bounds(start_date, end_date, tz_name)

        # Aggregate sold items
        sold_items = db.query(
            OrderItem.product_id,
            func.sum(OrderItem.quantity).label("quantity_sold"),
            func.sum(OrderItem.item_total).label("total_revenue")
        ).join(Order).filter(
            Order.status == "completed",
            Order.completed_at >= utc_start,
            Order.completed_at <= utc_end,
            OrderItem.is_cancelled == False
        ).group_by(OrderItem.product_id).all()

        sold_map = {item.product_id: (int(item.quantity_sold), Decimal(item.total_revenue)) for item in sold_items}

        # Fetch all active products
        all_products = db.query(Product).filter(Product.is_active == True).all()

        performance = []
        for p in all_products:
            if p.id in sold_map:
                qty, rev = sold_map[p.id]
                performance.append({
                    "product_id": p.id,
                    "sku": p.sku,
                    "name": p.name,
                    "quantity_sold": qty,
                    "total_revenue": rev,
                    "is_unsold": False
                })
            else:
                performance.append({
                    "product_id": p.id,
                    "sku": p.sku,
                    "name": p.name,
                    "quantity_sold": 0,
                    "total_revenue": Decimal("0.00"),
                    "is_unsold": True
                })

        # Top sold (must have sales, sorted by qty desc)
        top_sellers = [item for item in performance if item["quantity_sold"] > 0]
        top_sellers.sort(key=lambda x: (-x["quantity_sold"], -x["total_revenue"]))

        # Least sellers (sorted by qty asc)
        least_sellers = list(performance)
        least_sellers.sort(key=lambda x: (x["quantity_sold"], x["total_revenue"]))

        return {
            "start_date": start_date,
            "end_date": end_date,
            "top_products": top_sellers[:10],  # Top 10
            "least_selling_products": least_sellers[:10]  # Bottom 10
        }

    @classmethod
    def get_inventory_report(cls, db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None, tz_name: str = "UTC") -> Dict[str, Any]:
        """Check current stock levels and aggregate transaction movements."""
        # 1. Stock levels
        items = db.query(InventoryItem).all()
        stock_levels = []
        for item in items:
            prod_name = item.product.name if item.product else None
            is_low = item.current_quantity <= item.reorder_level
            stock_levels.append({
                "item_id": item.id,
                "item_name": item.item_name,
                "unit": item.unit,
                "current_quantity": Decimal(item.current_quantity),
                "reorder_level": Decimal(item.reorder_level),
                "is_low_stock": is_low,
                "product_name": prod_name
            })

        # Sort stock levels: put low stock first, then alphabetically
        stock_levels.sort(key=lambda x: (not x["is_low_stock"], x["item_name"]))

        # 2. Aggregated transaction movements
        movements = []
        if start_date and end_date:
            utc_start, utc_end = cls.get_datetime_bounds(start_date, end_date, tz_name)

            txs = db.query(
                InventoryTransaction.inventory_item_id,
                InventoryTransaction.transaction_type,
                func.sum(InventoryTransaction.quantity).label("total_qty"),
                func.count(InventoryTransaction.id).label("count")
            ).filter(
                InventoryTransaction.created_at >= utc_start,
                InventoryTransaction.created_at <= utc_end
            ).group_by(
                InventoryTransaction.inventory_item_id,
                InventoryTransaction.transaction_type
            ).all()

            item_map = {item.id: item for item in items}
            for tx in txs:
                inv_item = item_map.get(tx.inventory_item_id)
                if inv_item:
                    movements.append({
                        "item_id": tx.inventory_item_id,
                        "item_name": inv_item.item_name,
                        "unit": inv_item.unit,
                        "transaction_type": tx.transaction_type,
                        "total_quantity": Decimal(tx.total_qty),
                        "transaction_count": int(tx.count)
                    })

        return {
            "stock_levels": stock_levels,
            "movements": movements
        }

    @classmethod
    def get_employees_report(cls, db: Session, start_date: date, end_date: date, tz_name: str = "UTC") -> Dict[str, Any]:
        """Aggregate cashier performance statistics and retrieve shift logs."""
        utc_start, utc_end = cls.get_datetime_bounds(start_date, end_date, tz_name)

        # 1. Cashier sales performance
        cashier_sales = db.query(
            Order.cashier_id,
            func.count(Order.id).label("orders_count"),
            func.sum(Order.total_amount).label("sales_total")
        ).filter(
            Order.status == "completed",
            Order.completed_at >= utc_start,
            Order.completed_at <= utc_end
        ).group_by(Order.cashier_id).all()

        cashier_perf = []
        for row in cashier_sales:
            user = db.query(User).filter(User.id == row.cashier_id).first()
            if user:
                total = Decimal(row.sales_total)
                count = int(row.orders_count)
                aov = total / count if count > 0 else Decimal("0.00")
                cashier_perf.append({
                    "cashier_id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "orders_processed": count,
                    "total_sales": total,
                    "average_order_value": aov
                })

        cashier_perf.sort(key=lambda x: -x["total_sales"])

        # 2. Shift summaries
        shifts = db.query(Shift).filter(
            Shift.shift_date >= utc_start,
            Shift.shift_date <= utc_end
        ).all()

        shift_list = []
        for s in shifts:
            cashier_name = s.cashier.full_name if s.cashier else "Unknown Cashier"
            shift_list.append({
                "shift_id": s.id,
                "cashier_name": cashier_name,
                "shift_date": s.shift_date.date() if isinstance(s.shift_date, datetime) else s.shift_date,
                "opening_cash": Decimal(s.opening_cash) if s.opening_cash is not None else Decimal("0.00"),
                "expected_cash": Decimal(s.expected_cash) if s.expected_cash is not None else Decimal("0.00"),
                "actual_cash": Decimal(s.actual_cash) if s.actual_cash is not None else Decimal("0.00"),
                "cash_difference": Decimal(s.cash_difference) if s.cash_difference is not None else Decimal("0.00"),
                "status": s.status
            })

        return {
            "start_date": start_date,
            "end_date": end_date,
            "cashier_performance": cashier_perf,
            "shift_summaries": shift_list
        }

    @staticmethod
    def generate_csv_report(data: Dict[str, Any], report_type: str) -> str:
        """Serialize compiled reports metadata into standard, Excel-compatible CSV formats."""
        output = io.StringIO()
        writer = csv.writer(output)

        if report_type == "daily":
            writer.writerow(["Daily Operational Report", data["date"].strftime("%Y-%m-%d")])
            writer.writerow([])
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Total Completed Sales", f"{data['total_sales']:.2f}"])
            writer.writerow(["Net Payment Revenue", f"{data['net_revenue']:.2f}"])
            writer.writerow(["Completed Orders Count", data["order_count"]])
            writer.writerow(["Average Order Value (AOV)", f"{data['average_order_value']:.2f}"])
            writer.writerow(["Tax Collected", f"{data['tax_collected']:.2f}"])
            writer.writerow(["Discounts Granted", f"{data['discounts_given']:.2f}"])
            writer.writerow([])
            writer.writerow(["Orders Created by Status"])
            writer.writerow(["Status", "Count"])
            for status, count in data["orders_by_status"].items():
                writer.writerow([status.capitalize(), count])
            writer.writerow([])
            writer.writerow(["Payments Processed by Method"])
            writer.writerow(["Method", "Completed Transactions", "Amount Total"])
            for method, metrics in data["payments_by_method"].items():
                writer.writerow([method.upper(), metrics["count"], f"{metrics['total']:.2f}"])

        elif report_type == "trends":
            writer.writerow(["Sales and Order Trend Analysis"])
            writer.writerow(["Start Date", data["start_date"].strftime("%Y-%m-%d")])
            writer.writerow(["End Date", data["end_date"].strftime("%Y-%m-%d")])
            writer.writerow([])
            writer.writerow(["Date", "Sales Amount", "Order Count"])
            for pt in data["trends"]:
                writer.writerow([pt["date"], f"{pt['sales_amount']:.2f}", pt["order_count"]])

        elif report_type == "products":
            writer.writerow(["Product Performance Analytics"])
            writer.writerow(["Start Date", data["start_date"].strftime("%Y-%m-%d")])
            writer.writerow(["End Date", data["end_date"].strftime("%Y-%m-%d")])
            writer.writerow([])
            writer.writerow(["Top Selling Products"])
            writer.writerow(["SKU", "Product Name", "Quantity Sold", "Total Revenue"])
            for p in data["top_products"]:
                writer.writerow([p["sku"], p["name"], p["quantity_sold"], f"{p['total_revenue']:.2f}"])
            writer.writerow([])
            writer.writerow(["Least Selling / Unsold Products"])
            writer.writerow(["SKU", "Product Name", "Quantity Sold", "Total Revenue", "Status"])
            for p in data["least_selling_products"]:
                status = "Unsold" if p["is_unsold"] else "Active"
                writer.writerow([p["sku"], p["name"], p["quantity_sold"], f"{p['total_revenue']:.2f}", status])

        elif report_type == "inventory":
            writer.writerow(["Inventory Stock Levels & Movements"])
            writer.writerow([])
            writer.writerow(["Current Item Stock Levels"])
            writer.writerow(["Item Name", "Unit", "Current Quantity", "Reorder Level", "Low Stock Alert"])
            for s in data["stock_levels"]:
                alert = "YES - REORDER NOW" if s["is_low_stock"] else "Sufficient Stock"
                writer.writerow([s["item_name"], s["unit"], f"{s['current_quantity']:.2f}", f"{s['reorder_level']:.2f}", alert])
            writer.writerow([])
            writer.writerow(["Stock Transaction Movements in Period"])
            writer.writerow(["Item Name", "Unit", "Transaction Type", "Movement Quantity", "Transaction Count"])
            for m in data["movements"]:
                writer.writerow([m["item_name"], m["unit"], m["transaction_type"].replace("_", " ").upper(), f"{m['total_quantity']:.2f}", m["transaction_count"]])

        elif report_type == "employees":
            writer.writerow(["Employee Performance & Shifts Log"])
            writer.writerow(["Start Date", data["start_date"].strftime("%Y-%m-%d")])
            writer.writerow(["End Date", data["end_date"].strftime("%Y-%m-%d")])
            writer.writerow([])
            writer.writerow(["Cashier Sales Breakdown"])
            writer.writerow(["Username", "Full Name", "Orders Processed", "Total Sales Volume", "Average Ticket Value (AOV)"])
            for c in data["cashier_performance"]:
                writer.writerow([c["username"], c["full_name"], c["orders_processed"], f"{c['total_sales']:.2f}", f"{c['average_order_value']:.2f}"])
            writer.writerow([])
            writer.writerow(["Completed Shift Summaries"])
            writer.writerow(["Cashier Name", "Shift Date", "Opening Cash", "Expected Cash", "Actual Reconciled Cash", "Cash Difference", "Shift Status"])
            for s in data["shift_summaries"]:
                writer.writerow([s["cashier_name"], s["shift_date"].strftime("%Y-%m-%d"), f"{s['opening_cash']:.2f}", f"{s['expected_cash']:.2f}", f"{s['actual_cash']:.2f}", f"{s['cash_difference']:.2f}", s["status"]])

        return output.getvalue()

    @staticmethod
    def generate_pdf_report(data: Dict[str, Any], report_type: str) -> bytes:
        """Format compiled metrics into a branded, printable PDF document using ReportLab."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=inch*0.5,
            leftMargin=inch*0.5,
            topMargin=inch*0.5,
            bottomMargin=inch*0.5
        )

        styles = getSampleStyleSheet()
        # Custom premium style definitions
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            textColor=colors.HexColor('#2E7D32'),  # Premium Green brand theme
            spaceAfter=15
        )
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=11,
            textColor=colors.HexColor('#616161'),
            spaceAfter=15
        )
        section_style = ParagraphStyle(
            'ReportSection',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            textColor=colors.HexColor('#1B5E20'),
            spaceBefore=12,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            'ReportBody',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#212121')
        )

        story = []

        # Branded Header
        story.append(Paragraph("PANDA CAFE - OPERATIONAL ANALYTICS", title_style))

        if report_type == "daily":
            story.append(Paragraph(f"Daily Operational Report for {data['date'].strftime('%Y-%m-%d')}", subtitle_style))
            story.append(Spacer(1, 10))

            # Table representation of key sales metrics
            metrics_table_data = [
                [Paragraph("<b>Financial Metric</b>", body_style), Paragraph("<b>Value</b>", body_style)],
                ["Total Completed Sales", f"${data['total_sales']:.2f}"],
                ["Net Payment Revenue", f"${data['net_revenue']:.2f}"],
                ["Completed Orders Count", str(data["order_count"])],
                ["Average Order Value (AOV)", f"${data['average_order_value']:.2f}"],
                ["Tax Collected", f"${data['tax_collected']:.2f}"],
                ["Discounts Granted", f"${data['discounts_given']:.2f}"],
            ]

            t = Table(metrics_table_data, colWidths=[3.5*inch, 3*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E8F5E9')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#1B5E20')),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#C8E6C9')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9F9F9')])
            ]))
            story.append(t)
            story.append(Spacer(1, 15))

            # Orders by status section
            story.append(Paragraph("Orders Status Breakdown", section_style))
            status_data = [["Order Status", "Count"]]
            for status, count in data["orders_by_status"].items():
                status_data.append([status.capitalize(), str(count)])
            t_status = Table(status_data, colWidths=[3.5*inch, 3*inch])
            t_status.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F8E9')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DCEDC8')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#FAFAFA')]),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('TOPPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(t_status)

        elif report_type == "trends":
            story.append(Paragraph(f"Sales & Order Trends: {data['start_date']} to {data['end_date']}", subtitle_style))
            story.append(Spacer(1, 10))

            trend_table = [["Date", "Sales Volume", "Order Volume"]]
            for pt in data["trends"]:
                trend_table.append([pt["date"], f"${pt['sales_amount']:.2f}", str(pt["order_count"])])

            t = Table(trend_table, colWidths=[2.5*inch, 2.5*inch, 2*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E8F5E9')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#C8E6C9')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9F9F9')]),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('TOPPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(t)

        elif report_type == "products":
            story.append(Paragraph(f"Product Sales Metrics: {data['start_date']} to {data['end_date']}", subtitle_style))
            story.append(Spacer(1, 10))

            story.append(Paragraph("Top Performing Products", section_style))
            top_table = [["SKU", "Product Name", "Units Sold", "Gross Revenue"]]
            for p in data["top_products"]:
                top_table.append([p["sku"], p["name"], str(p["quantity_sold"]), f"${p['total_revenue']:.2f}"])

            t_top = Table(top_table, colWidths=[1.5*inch, 2.5*inch, 1.5*inch, 1.5*inch])
            t_top.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#C8E6C9')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#A5D6A7')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F5F5F5')]),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('TOPPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(t_top)
            story.append(Spacer(1, 15))

            story.append(Paragraph("Least Performing & Unsold Products", section_style))
            least_table = [["SKU", "Product Name", "Units Sold", "Gross Revenue", "Status"]]
            for p in data["least_selling_products"]:
                status = "Unsold" if p["is_unsold"] else "Active"
                least_table.append([p["sku"], p["name"], str(p["quantity_sold"]), f"${p['total_revenue']:.2f}", status])

            t_least = Table(least_table, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 1.3*inch, 1*inch])
            t_least.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#FFEBEE')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#FFCDD2')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#FAFAFA')]),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('TOPPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(t_least)

        elif report_type == "inventory":
            story.append(Paragraph("Inventory Management & Transaction Logs", subtitle_style))
            story.append(Spacer(1, 10))

            story.append(Paragraph("Ingredient / Stock Levels", section_style))
            levels_table = [["Item Name", "Unit", "Current Stock", "Reorder Trigger Level", "Status"]]
            for s in data["stock_levels"]:
                alert = Paragraph("<font color='red'><b>LOW STOCK</b></font>", body_style) if s["is_low_stock"] else "Normal"
                levels_table.append([s["item_name"], s["unit"], f"{s['current_quantity']:.2f}", f"{s['reorder_level']:.2f}", alert])

            t_levels = Table(levels_table, colWidths=[2*inch, 1*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            t_levels.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E0F2F1')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#B2DFDB')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9F9F9')]),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('TOPPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(t_levels)

            if data["movements"]:
                story.append(Spacer(1, 15))
                story.append(Paragraph("Stock Movement Audit", section_style))
                mov_table = [["Item Name", "Unit", "Transaction Type", "Movement Volume", "Tx Count"]]
                for m in data["movements"]:
                    tx_type = m["transaction_type"].replace("_", " ").upper()
                    mov_table.append([m["item_name"], m["unit"], tx_type, f"{m['total_quantity']:.2f}", str(m["transaction_count"])])

                t_mov = Table(mov_table, colWidths=[2*inch, 1*inch, 2*inch, 1.5*inch, 1*inch])
                t_mov.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#ECEFF1')),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CFD8DC')),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9FAFC')]),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                    ('TOPPADDING', (0,0), (-1,-1), 4),
                ]))
                story.append(t_mov)

        elif report_type == "employees":
            story.append(Paragraph(f"Cashier Performance & Shift Reconciliations: {data['start_date']} to {data['end_date']}", subtitle_style))
            story.append(Spacer(1, 10))

            story.append(Paragraph("Cashier Sales Performance", section_style))
            cashier_table = [["Cashier Username", "Full Name", "Orders Count", "Sales Completed", "AOV"]]
            for c in data["cashier_performance"]:
                cashier_table.append([c["username"], c["full_name"], str(c["orders_processed"]), f"${c['total_sales']:.2f}", f"${c['average_order_value']:.2f}"])

            t_cashier = Table(cashier_table, colWidths=[1.5*inch, 2*inch, 1.2*inch, 1.5*inch, 1.3*inch])
            t_cashier.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E8F5E9')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#C8E6C9')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9F9F9')]),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('TOPPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(t_cashier)
            story.append(Spacer(1, 15))

            story.append(Paragraph("Cashier Shift Reconciliations", section_style))
            shifts_table = [["Cashier Name", "Shift Date", "Opening Cash", "Expected Cash", "Actual Cash", "Difference", "Status"]]
            for s in data["shift_summaries"]:
                diff = s["cash_difference"]
                diff_str = f"${diff:.2f}"
                if diff != 0:
                    diff_str = f"${diff:.2f} (!)"
                shifts_table.append([
                    s["cashier_name"],
                    s["shift_date"].strftime("%Y-%m-%d"),
                    f"${s['opening_cash']:.2f}",
                    f"${s['expected_cash']:.2f}",
                    f"${s['actual_cash']:.2f}",
                    diff_str,
                    s["status"].upper()
                ])

            t_shifts = Table(shifts_table, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch, 1*inch, 1*inch, 1*inch])
            t_shifts.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F8E9')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DCEDC8')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#FAFAFA')]),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('FONTSIZE', (0,0), (-1,-1), 9),
            ]))
            story.append(t_shifts)

        # Build Document
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
