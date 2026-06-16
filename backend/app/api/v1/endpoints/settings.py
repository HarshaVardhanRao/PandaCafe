import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Setting, User, Role
from app.api.v1.endpoints.inventory import get_current_user
from app.schemas.setting import UPISettingResponse, UPISettingUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["Settings"])


def check_admin_access(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    """Restricts settings edits to Owner or Manager roles."""
    role = db.query(Role).filter(Role.id == current_user.role_id).first()
    role_name = role.name.lower() if role else ""
    if role_name not in ["owner", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Owner or Manager privileges required."
        )
    return current_user


@router.get("/upi_id", response_model=UPISettingResponse)
def get_upi_id(db: Session = Depends(get_db)):
    """Retrieve the store's UPI ID setting."""
    setting = db.query(Setting).filter(Setting.setting_key == "upi_id").first()
    if not setting:
        return UPISettingResponse(upi_id="pandacafe@upi")
    return UPISettingResponse(upi_id=setting.setting_value)


@router.put("/upi_id", response_model=UPISettingResponse)
def update_upi_id(
    request: UPISettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin_access)
):
    """Update the store's UPI ID setting. Only accessible by Owner/Manager."""
    try:
        setting = db.query(Setting).filter(Setting.setting_key == "upi_id").first()
        if not setting:
            setting = Setting(
                setting_key="upi_id",
                setting_value=request.upi_id,
                setting_type="string",
                description="UPI ID for payment QR code generation",
                is_system=True,
                updated_by=current_user.id
            )
            db.add(setting)
        else:
            setting.setting_value = request.upi_id
            setting.updated_by = current_user.id
            setting.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(setting)
        return UPISettingResponse(upi_id=setting.setting_value)
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating UPI ID: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update settings"
        )
