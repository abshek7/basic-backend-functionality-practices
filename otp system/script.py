from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import random, string

otp_store = {}

app = FastAPI()

class OTPRequest(BaseModel):
    email: EmailStr

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str

def generate_otp(length: int = 6) -> str:
    return ''.join(random.choices(string.digits, k=length))

@app.post("/generate-otp")
def generate_otp_for_user(data: OTPRequest):
    otp = generate_otp()
    expiry = datetime.utcnow() + timedelta(minutes=5)
    otp_store[data.email] = {"otp": otp, "expiry": expiry}

    print(f"Sending OTP to {data.email}: {otp}")

    return {"message": "OTP sent successfully"}

@app.post("/verify-otp")
def verify_otp(data: OTPVerify):
    record = otp_store.get(data.email)

    if not record:
        raise HTTPException(status_code=400, detail="No OTP found for this email")

    if datetime.now()> record["expiry"]:
        raise HTTPException(status_code=400, detail="OTP expired")

    if data.otp != record["otp"]:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # OTP is valid → remove from store to prevent reuse
    del otp_store[data.email]

    return {"message": "OTP verified successfully"}
