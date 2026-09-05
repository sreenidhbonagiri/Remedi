from pydantic import BaseModel, Field


class ApplicationPDFRequest(BaseModel):
    patient_name: str = Field(..., min_length=1, examples=["Maria Chen"])
    medication_name: str = Field(..., min_length=1, examples=["Humira"])
    annual_income: float = Field(..., ge=0, examples=[35000])
    household_size: int = Field(..., ge=1, le=20, examples=[1])
    state: str = Field(..., min_length=2, max_length=32, examples=["IL"])
    is_uninsured: bool = Field(..., examples=[True])
    program_name: str = Field(..., min_length=1, examples=["myAbbVie Assist"])


class MedicationOut(BaseModel):
    id: int
    name: str
    generic_name: str
    strength: str
    form: str
    program_id: int

    model_config = {"from_attributes": True}


class ProgramOut(BaseModel):
    id: int
    name: str
    manufacturer: str
    fpl_limit_percent: float
    description: str
    phone: str
    mailing_address: str
    medications: list[MedicationOut] = []

    model_config = {"from_attributes": True}
