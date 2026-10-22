from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerCreate(BaseModel):
    business_name: str = Field(min_length=2, max_length=150)
    email: EmailStr


class CustomerResponse(CustomerCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class AccountResponse(BaseModel):
    id: int
    customer_id: int
    currency: str
    balance_pence: int = Field(ge=0)


class TransactionResponse(BaseModel):
    id: int
    from_account_id: int
    to_account_id: int
    amount_pence: int = Field(gt=0)
    created_at: str
