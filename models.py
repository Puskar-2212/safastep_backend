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
