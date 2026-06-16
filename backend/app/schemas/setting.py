from pydantic import BaseModel, Field

class UPISettingResponse(BaseModel):
    upi_id: str

class UPISettingUpdate(BaseModel):
    upi_id: str = Field(..., description="UPI ID for payment QR code generation")
