"""
API endpoints for bill and receipt sharing (simulation).
"""

import logging
import urllib.parse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import User, OrderItem, Product
from app.api.v1.endpoints.inventory import get_current_user
from app.schemas.customer import BillShareRequest
from app.services.order_service import OrderService
from app.services.billing_service import BillingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Bill Sharing"])


@router.post("/orders/{order_id}/share", status_code=status.HTTP_200_OK)
def share_bill(
    order_id: UUID,
    request: BillShareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Simulate sharing of the order bill/receipt via Email, WhatsApp, or SMS.
    Output is written to mock text files in the backend folder.
    """
    # 1. Fetch order
    order = OrderService.get_order(db, str(order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 2. Get billing totals
    billing = BillingService.calculate_order_totals(db, str(order_id))

    # 3. Format items list
    items = db.query(OrderItem).filter(
        OrderItem.order_id == order_id,
        OrderItem.is_cancelled == False
    ).all()

    items_text = ""
    for item in items:
        prod = db.query(Product).filter(Product.id == item.product_id).first()
        prod_name = prod.name if prod else "Unknown Item"
        items_text += f"\n- {prod_name} x {item.quantity}: {item.item_total:.2f}"

    # 4. Create sharing contents
    receipt = (
        f"========================================\n"
        f"               PANDA CAFE               \n"
        f"========================================\n"
        f"Receipt for Order: {order.order_number}\n"
        f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"----------------------------------------"
        f"{items_text}\n"
        f"----------------------------------------\n"
        f"Subtotal:       {billing['subtotal']:.2f}\n"
        f"Tax Amount:     {billing['tax_amount']:.2f}\n"
        f"Discount:       {billing['discount_amount']:.2f}\n"
        f"Total Amount:   {billing['total_amount']:.2f}\n"
        f"========================================\n"
    )

    import os
    base_path = ""
    if os.path.basename(os.getcwd()) != "backend" and os.path.exists("backend"):
        base_path = "backend"

    method = request.method.lower()
    dest = request.destination

    if method == "email":
        sim_file = os.path.join(base_path, "email_simulation.txt")
        log_entry = (
            f"--- EMAIL TO: {dest} at {order.updated_at.isoformat()} ---\n"
            f"Subject: Your Panda Cafe Receipt - {order.order_number}\n\n"
            f"{receipt}\n"
            f"-----------------------------------------------------------\n\n"
        )
        try:
            with open(sim_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
            logger.info(f"Simulated email sent to {dest} for order {order.order_number}")
            return {"message": f"Simulated email receipt sent successfully to {dest}"}
        except Exception as e:
            logger.error(f"Error writing email simulation: {str(e)}")
            raise HTTPException(status_code=500, detail="Error writing email simulation file")

    elif method == "whatsapp":
        sim_file = os.path.join(base_path, "whatsapp_simulation.txt")
        log_entry = (
            f"--- WHATSAPP TO: {dest} at {order.updated_at.isoformat()} ---\n"
            f"Message Body:\n{receipt}\n"
            f"--------------------------------------------------------------\n\n"
        )
        try:
            with open(sim_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
            logger.info(f"Simulated WhatsApp message logged for {dest}")

            # Return clickable wa.me URL link for WhatsApp redirection
            encoded_text = urllib.parse.quote(receipt)
            wa_link = f"https://wa.me/{dest.replace('+', '')}?text={encoded_text}"

            return {
                "message": f"Simulated WhatsApp receipt logged successfully for {dest}",
                "whatsapp_link": wa_link,
            }
        except Exception as e:
            logger.error(f"Error writing WhatsApp simulation: {str(e)}")
            raise HTTPException(status_code=500, detail="Error writing WhatsApp simulation file")

    elif method == "sms":
        sim_file = os.path.join(base_path, "sms_simulation.txt")
        sms_text = f"Panda Cafe bill for {order.order_number}. Total: {billing['total_amount']:.2f}. Thank you!"
        log_entry = (
            f"--- SMS TO: {dest} at {order.updated_at.isoformat()} ---\n"
            f"Text: {sms_text}\n"
            f"---------------------------------------------------------\n\n"
        )
        try:
            with open(sim_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
            logger.info(f"Simulated SMS logged to {dest} for order {order.order_number}")
            return {"message": f"Simulated SMS receipt sent successfully to {dest}"}
        except Exception as e:
            logger.error(f"Error writing SMS simulation: {str(e)}")
            raise HTTPException(status_code=500, detail="Error writing SMS simulation file")
