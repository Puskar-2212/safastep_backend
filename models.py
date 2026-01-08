from pydantic import BaseModel

class OTPRequest(BaseModel):
    countryCode: str
    mobile: str

class VerifyOTP(BaseModel):
    mobile: str
    otp: str
    userData: dict

class SignupRequest(BaseModel):
    firstName: str
    lastName: str
    dateOfBirth: dict
    pin: str
    mobile: str

class LoginRequest(BaseModel):
    mobile: str
    pin: str

class VerifyPinResetOTP(BaseModel):
    mobile: str
    otp: str
    new_pin: str

class CreatePost(BaseModel):
    mobile: str
    caption: str
    category: str
    categoryId: str

class UpdateSteps(BaseModel):
    mobile: str
    steps: int

class LikePost(BaseModel):
    mobile: str

class CarbonFootprintResult(BaseModel):
    mobile: str
    totalCO2: float
    yearlyTons: float
    treesNeeded: int
    impactLevel: str
    breakdown: dict
    vsGlobalAverage: dict
    questionsAnswered: int

# Eco-Location Models
from typing import Optional, Dict, List
from pydantic import validator, Field
from datetime import datetime

class ContactInfo(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None

class LocationCoordinates(BaseModel):
    latitude: float = Field(..., ge=27.6, le=27.8, description="Latitude within Kathmandu valley")
    longitude: float = Field(..., ge=85.2, le=85.5, description="Longitude within Kathmandu valley")

class EcoLocationBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    category: str
    description: str
    city: str
    latitude: float = Field(..., ge=27.6, le=27.8)
    longitude: float = Field(..., ge=85.2, le=85.5)
    address: str
    contact: Optional[ContactInfo] = None
    hours: Optional[Dict[str, str]] = None
    amenities: Optional[List[str]] = None
    images: Optional[List[str]] = None
    
    @validator('category')
    def validate_category(cls, v):
        valid_categories = ['plantation_event', 'ngo_office', 'recycling_center', 'community_garden', 'eco_store']
        if v not in valid_categories:
            raise ValueError(f'Category must be one of: {", ".join(valid_categories)}')
        return v
    
    @validator('city')
    def validate_city(cls, v):
        valid_cities = ['Kathmandu', 'Bhaktapur', 'Lalitpur']
        if v not in valid_cities:
            raise ValueError(f'City must be one of: {", ".join(valid_cities)}')
        return v

class PlantationEventFields(BaseModel):
    eventDate: str
    startTime: str
    endTime: str
    organizer: str
    targetTrees: Optional[int] = None
    volunteersNeeded: Optional[int] = None
    volunteersRegistered: Optional[int] = 0
    estimatedCO2Offset: Optional[str] = None
    status: str = "upcoming"
    
    @validator('eventDate')
    def validate_event_date(cls, v):
        try:
            event_date = datetime.fromisoformat(v.replace('Z', '+00:00'))
            if event_date.date() < datetime.now().date():
                raise ValueError('Event date cannot be in the past')
        except ValueError as e:
            if 'past' in str(e):
                raise e
            raise ValueError('Invalid date format. Use ISO format (YYYY-MM-DD)')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['upcoming', 'ongoing', 'completed']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v

class EcoLocationCreate(EcoLocationBase):
    """Model for creating a new eco-location"""
    # Event-specific fields (optional, only for plantation_event category)
    eventDate: Optional[str] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    organizer: Optional[str] = None
    targetTrees: Optional[int] = None
    volunteersNeeded: Optional[int] = None
    volunteersRegistered: Optional[int] = 0
    estimatedCO2Offset: Optional[str] = None
    status: Optional[str] = "upcoming"
    
    @validator('eventDate')
    def validate_event_date_if_present(cls, v, values):
        if v and values.get('category') == 'plantation_event':
            try:
                event_date = datetime.fromisoformat(v.replace('Z', '+00:00'))
                if event_date.date() < datetime.now().date():
                    raise ValueError('Event date cannot be in the past')
            except ValueError as e:
                if 'past' in str(e):
                    raise e
                raise ValueError('Invalid date format. Use ISO format (YYYY-MM-DD)')
        return v

class EcoLocationUpdate(BaseModel):
    """Model for updating an existing eco-location"""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    category: Optional[str] = None
    description: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=27.6, le=27.8)
    longitude: Optional[float] = Field(None, ge=85.2, le=85.5)
    address: Optional[str] = None
    contact: Optional[ContactInfo] = None
    hours: Optional[Dict[str, str]] = None
    amenities: Optional[List[str]] = None
    images: Optional[List[str]] = None
    eventDate: Optional[str] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    organizer: Optional[str] = None
    targetTrees: Optional[int] = None
    volunteersNeeded: Optional[int] = None
    volunteersRegistered: Optional[int] = None
    estimatedCO2Offset: Optional[str] = None
    status: Optional[str] = None
    
    @validator('category')
    def validate_category(cls, v):
        if v is not None:
            valid_categories = ['plantation_event', 'ngo_office', 'recycling_center', 'community_garden', 'eco_store']
            if v not in valid_categories:
                raise ValueError(f'Category must be one of: {", ".join(valid_categories)}')
        return v
    
    @validator('city')
    def validate_city(cls, v):
        if v is not None:
            valid_cities = ['Kathmandu', 'Bhaktapur', 'Lalitpur']
            if v not in valid_cities:
                raise ValueError(f'City must be one of: {", ".join(valid_cities)}')
        return v
