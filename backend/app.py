from email.message import EmailMessage
from multiprocessing.connection import Client
import os
import smtplib
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import List
from sqlalchemy import Column, Integer, String, Float, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from fastapi.middleware.cors import CORSMiddleware
import random
from dotenv import load_dotenv

# Database setup
DATABASE_URL = "mysql+pymysql://root:{your_password}@localhost/{your_db}"
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables
Base.metadata.create_all(bind=engine)

# FastAPI App
app = FastAPI(title="OTP Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],  # List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Load environment variables from a .env file
load_dotenv()


# A simple in-memory store for OTPs (use a database for production)
otp_store = {}

# Environment variables for email credentials
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")  # Your email address
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # Your email app password

if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
    raise Exception("Please set EMAIL_ADDRESS and EMAIL_PASSWORD in your environment variables.")

# Request model for email
class OTPRequest(BaseModel):
    email: EmailStr

# Send OTP endpoint

@app.post("/send-otp")
async def send_otp(request: OTPRequest):
    # Generate a 6-digit OTP
    otp = random.randint(100000, 999999)

    # Send OTP via email
    try:
        # Create an HTML email message
        msg = EmailMessage()
        msg.set_content(
            f"""\
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: #f9f9f9;
            margin: 0;
            padding: 0;
        }}
        .email-container {{
            max-width: 600px;
            margin: 20px auto;
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            text-align: center;
            font-size: 20px;
            font-weight: bold;
            color: #333333;
        }}
        .otp {{
            font-size: 32px;
            font-weight: bold;
            color: #1a73e8;
            text-align: center;
            margin: 20px 0;
        }}
        .message {{
            font-size: 16px;
            line-height: 1.5;
            color: #555555;
            text-align: justify;
        }}
        .footer {{
            margin-top: 20px;
            text-align: center;
            font-size: 12px;
            color: #888888;
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">Your OTP Verification Code</div>
        <p class="message">
            Dear User,<br><br>
            Your One-Time Password (OTP) is:
        </p>
        <div class="otp">{otp}</div>
        <p class="message">
            Please use this OTP to complete your verification process. This code is valid for the next 
            <strong>10 minutes</strong>. Do not share this code with anyone.<br><br>
            If you did not request this OTP, please ignore this email.
        </p>
        <div class="footer">
            Thank you,<br>
            <strong>Your_company_name</strong>
        </div>
    </div>
</body>
</html>
""",
            subtype="html",
        )
        msg["Subject"] = "Your OTP Code - Verification Required"
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = request.email

        # Send the email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send OTP: {str(e)}")

    # Store OTP
    otp_store[request.email] = otp
    return {"message": f"OTP sent successfully to: {msg['To']}"}

# OTP verification endpoint
class OTPVerificationRequest(BaseModel):
    email: EmailStr
    otp: int

@app.post("/verify-otp")
async def verify_otp(request: OTPVerificationRequest):
    if request.email not in otp_store:
        raise HTTPException(status_code=400, detail="Email not found")

    if otp_store[request.email] != request.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # OTP verified successfully; remove it from the store
    del otp_store[request.email]
    return {"message": "OTP verified successfully"}
