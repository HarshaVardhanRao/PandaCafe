"""
Printer Service - Simulates Kitchen Order Ticket (KOT) printing.
"""
import os
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Order, OrderItem, Product, Table

class PrinterService:
    @staticmethod
    def print_kot(db: Session, order: Order) -> None:
        """
        Formats and simulates printing a KOT (Kitchen Order Ticket).
        Appends the formatted text to printer_simulation.txt in the app root directory.
        """
        # Fetch related items
        items = db.query(OrderItem).filter(
            OrderItem.order_id == order.id,
            OrderItem.is_cancelled == False
        ).all()
        
        if not items:
            return
            
        # Get table info if dine_in
        table_number = "N/A"
        if order.order_type == "dine_in" and order.table_id:
            table = db.query(Table).filter(Table.id == order.table_id).first()
            if table:
                table_number = str(table.table_number)

        # Build KOT string
        lines = []
        lines.append("================================")
        lines.append("           PANDA CAFE           ")
        lines.append("================================")
        lines.append(f"KOT: {order.order_number}")
        
        # Order Type / Table
        order_type_display = "Dine In" if order.order_type == "dine_in" else "Take Away"
        if order.order_type == "dine_in":
            lines.append(f"Type: {order_type_display} | Table: {table_number}")
        else:
            lines.append(f"Type: {order_type_display}")
            
        time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"Time: {time_str}")
        lines.append("--------------------------------")
        lines.append("Qty   Item             Notes")
        lines.append("--------------------------------")
        
        for item in items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            product_name = product.name if product else "Unknown Item"
            notes = item.special_notes or ""
            
            # Format quantity (e.g. left aligned, 5 spaces total width)
            # Format item name (left aligned, 16 spaces total width)
            # Format notes (remaining)
            qty_str = f"{item.quantity:<5}"
            name_str = f"{product_name:<16}"
            line = f"{qty_str} {name_str} {notes}".rstrip()
            lines.append(line)
            
        lines.append("================================")
        lines.append("\n\n") # Separation for multiple tickets
        
        kot_text = "\n".join(lines)
        
        # Append to printer_simulation.txt
        # Let's ensure the path is correct inside container
        filepath = os.path.join(os.getcwd(), "printer_simulation.txt")
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(kot_text)
        except Exception as e:
            # log or handle exception silently so printing doesn't break app flow
            import logging
            logging.getLogger(__name__).error(f"Failed to write printer simulation KOT: {e}")
