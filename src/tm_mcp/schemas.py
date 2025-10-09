"""Pydantic schemas describing backend payloads."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, PositiveInt, TypeAdapter, model_validator


class Property(BaseModel):
    id: PositiveInt
    address: str = Field(min_length=1)
    rent: float
    maintenance: float

    model_config = {"extra": "ignore"}


property_adapter = TypeAdapter(Property)
property_list_adapter = TypeAdapter(list[Property])


class PropertyInput(BaseModel):
    address: str = Field(min_length=1)
    rent: float
    maintenance: float


class PropertyUpdate(PropertyInput):
    id: PositiveInt


class TenantBase(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    propertyId: Optional[PositiveInt] = None
    passport: Optional[str] = Field(default=None, min_length=1)
    passportValidity: Optional[str] = Field(default=None, min_length=1)
    aadharNo: Optional[str] = Field(default=None, min_length=1)
    employmentDetails: Optional[str] = Field(default=None, min_length=1)
    permanentAddress: Optional[str] = Field(default=None, min_length=1)
    contactNo: Optional[str] = Field(default=None, min_length=1)
    emergencyContactNo: Optional[str] = Field(default=None, min_length=1)
    rent: Optional[float] = None
    security: Optional[float] = None
    moveInDate: Optional[str] = Field(default=None, min_length=1)
    contractStartDate: Optional[str] = Field(default=None, min_length=1)
    contractExpiryDate: Optional[str] = Field(default=None, min_length=1)

    model_config = {"extra": "ignore"}


class Tenant(BaseModel):
    id: PositiveInt
    name: str = Field(min_length=1)
    propertyId: PositiveInt
    propertyAddress: Optional[str] = None
    passport: Optional[str] = None
    passportValidity: Optional[str] = None
    aadharNo: Optional[str] = None
    employmentDetails: Optional[str] = None
    permanentAddress: Optional[str] = None
    contactNo: Optional[str] = None
    emergencyContactNo: Optional[str] = None
    rent: Optional[float] = None
    security: Optional[float] = None
    moveInDate: Optional[str] = None
    contractStartDate: Optional[str] = None
    contractExpiryDate: Optional[str] = None

    model_config = {"extra": "ignore"}


tenant_adapter = TypeAdapter(Tenant)
tenant_list_adapter = TypeAdapter(list[Tenant])


class TenantCreate(TenantBase):
    name: str = Field(min_length=1)
    propertyId: PositiveInt


class TenantUpdate(TenantBase):
    @model_validator(mode="after")
    def ensure_at_least_one_field(cls, model: "TenantUpdate") -> "TenantUpdate":
        payload = model.model_dump(exclude_none=True)
        if not payload:
            raise ValueError("At least one field must be provided to update a tenant.")
        return model


class TenantUpdatePayload(TenantUpdate):
    id: PositiveInt

    @model_validator(mode="after")
    def ensure_fields_present(cls, model: "TenantUpdatePayload") -> "TenantUpdatePayload":
        payload = model.model_dump(exclude_none=True)
        payload.pop("id", None)
        if not payload:
            raise ValueError("At least one field must be provided to update a tenant.")
        return model


class Transaction(BaseModel):
    id: PositiveInt
    propertyId: PositiveInt
    propertyAddress: Optional[str] = None
    tenantId: Optional[PositiveInt] = None
    tenantName: Optional[str] = None
    type: "TransactionType"
    forMonth: Optional[str] = None
    amount: float
    transactionDate: str = Field(min_length=1)
    comments: Optional[str] = None

    model_config = {"extra": "ignore"}


transaction_adapter = TypeAdapter(Transaction)
transaction_list_adapter = TypeAdapter(list[Transaction])


class TransactionCreate(BaseModel):
    propertyId: PositiveInt
    tenantId: Optional[PositiveInt] = None
    type: "TransactionType"
    forMonth: Optional[str] = None
    amount: float
    transactionDate: str = Field(min_length=1)
    comments: Optional[str] = None


class TransactionUpdate(BaseModel):
    propertyId: Optional[PositiveInt] = None
    tenantId: Optional[PositiveInt] = None
    type: Optional["TransactionType"] = None
    forMonth: Optional[str] = None
    amount: Optional[float] = None
    transactionDate: Optional[str] = Field(default=None, min_length=1)
    comments: Optional[str] = None

    @model_validator(mode="after")
    def ensure_at_least_one_field(cls, model: "TransactionUpdate") -> "TransactionUpdate":
        payload = model.model_dump(exclude_none=True)
        if not payload:
            raise ValueError("At least one field must be provided to update a transaction.")
        return model


class TransactionUpdatePayload(TransactionUpdate):
    id: PositiveInt

    @model_validator(mode="after")
    def ensure_fields_present(cls, model: "TransactionUpdatePayload") -> "TransactionUpdatePayload":
        payload = model.model_dump(exclude_none=True)
        payload.pop("id", None)
        if not payload:
            raise ValueError("At least one field must be provided to update a transaction.")
        return model


class TransactionType(str, Enum):
    RENT = "rent"
    SECURITY = "security"
    PAYMENT_RECEIVED = "payment_received"
    GAS = "gas"
    ELECTRICITY = "electricity"
    WATER = "water"
    MAINTENANCE = "maintenance"
    MISC = "misc"
