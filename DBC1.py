import os
import urllib.parse
from sqlalchemy import create_engine, Column, Integer, String, text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from contextlib import contextmanager
from datetime import datetime
import uvicorn

# --- DATABASE CONFIGURATION ---
DB_USER = "root"
DB_PASSWORD = urllib.parse.quote_plus("Johncena@15")
DB_HOST = "localhost"
DB_NAME = "sqldb"

connection_uri = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# SQLAlchemy setup
engine = create_engine(connection_uri)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODEL DEFINITION ---
class FromEnvironment(Base):
    __tablename__ = "from_environment"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(Integer, nullable=False)  # Integer type
    environment = Column(String(100))
    customer_name = Column(String(200), nullable=False)
    process = Column(String(100))
    tab_name = Column(String(200))
    section_name = Column(String(200))
    field_name = Column(String(200))
    field_type = Column(String(100))
    action = Column(String(100))

# --- CREATE TABLES ---
Base.metadata.create_all(bind=engine)

# --- PYDANTIC MODELS ---
class FromEnvironmentCreate(BaseModel):
    request_id: int  # Integer type
    environment: Optional[str] = None
    customer_name: str
    process: Optional[str] = None
    tab_name: Optional[str] = None
    section_name: Optional[str] = None
    field_name: Optional[str] = None
    field_type: Optional[str] = None
    action: Optional[str] = None

class FromEnvironmentResponse(BaseModel):
    id: int
    request_id: int  # Integer type
    environment: Optional[str]
    customer_name: str
    process: Optional[str]
    tab_name: Optional[str]
    section_name: Optional[str]
    field_name: Optional[str]
    field_type: Optional[str]
    action: Optional[str]

    class Config:
        from_attributes = True

# --- DATABASE SESSION CONTEXT MANAGER ---
@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- HELPER FUNCTIONS ---
def populate_sample_data_for_customers(request_id: int, customer_names: List[str], db: Session):
    """Populate sample data for specified customers"""
    
    sample_templates = {
        "IBM": [
            {"environment": "prodnci", "process": "retrieval", "tab_name": "Service Details", "section_name": "Footer", "field_name": "About", "field_type": "text", "action": "retrieve"},
            {"environment": "prodnci", "process": "retrieval", "tab_name": "Service Details", "section_name": "Footer", "field_name": "Version", "field_type": "text", "action": "retrieve"},
            {"environment": "b3ft", "process": "filling", "tab_name": "Service Details", "section_name": "Footer", "field_name": "Powered by", "field_type": "text", "action": "browser_type"},
            {"environment": "prodnci", "process": "retrieval", "tab_name": "Employer-General", "section_name": "General", "field_name": "Employer Sector", "field_type": "dropdown", "action": "retrieve"},
            {"environment": "b3ft", "process": "filling", "tab_name": "Employer-General", "section_name": "General", "field_name": "Employer Sector", "field_type": "dropdown", "action": "browser_select_option"},
            {"environment": "prodnci", "process": "retrieval", "tab_name": "Employer-General", "section_name": "General", "field_name": "Company Name", "field_type": "textbox", "action": "retrieve"},
            {"environment": "b3ft", "process": "filling", "tab_name": "Employer-General", "section_name": "General", "field_name": "Company Name", "field_type": "textbox", "action": "browser_type"},
            {"environment": "prodnci", "process": "retrieval", "tab_name": "Service Details", "section_name": "General", "field_name": "Service Type", "field_type": "dropdown", "action": "retrieve"},
            {"environment": "b3ft", "process": "filling", "tab_name": "Service Details", "section_name": "General", "field_name": "Service Type", "field_type": "dropdown", "action": "browser_select_option"},
            {"environment": "prodnci", "process": "retrieval", "tab_name": "Integrated_Program", "section_name": "Employee Distribution", "field_name": "Total Employees", "field_type": "text", "action": "retrieve"},
            # Missing fields in retrieval
            {"environment": None, "process": "retrieval", "tab_name": None, "section_name": "General", "field_name": "Area", "field_type": "textbox", "action": None},
            {"environment": "prodnci", "process": "retrieval", "tab_name": "Employer-General", "section_name": None, "field_name": "Company Size", "field_type": None, "action": "retrieve"},
            # Missing fields in filling
            {"environment": None, "process": "filling", "tab_name": None, "section_name": "Footer", "field_name": "Copyright", "field_type": "text", "action": None},
            {"environment": "b3ft", "process": "filling", "tab_name": "Service Details", "section_name": None, "field_name": "Terms", "field_type": None, "action": "browser_type"},
            {"environment": "b3ft", "process": "filling", "tab_name": None, "section_name": "Footer", "field_name": "Terms", "field_type": None, "action": "browser_type"},

        ],
        "CITY OF ADELANTO": [
            {"environment": "b3ft", "process": "filling", "tab_name": "Integrated_Program", "section_name": "Employee Distribution", "field_name": "Absence Management", "field_type": "radio_button", "action": "browser_click"},
            {"environment": "prodnci", "process": "retrieval", "tab_name": "Integrated_Program", "section_name": "Employee Distribution", "field_name": "Leave Type", "field_type": "dropdown", "action": "retrieve"},
            {"environment": "b3ft", "process": "filling", "tab_name": "Integrated_Program", "section_name": "Employee Distribution", "field_name": "Leave Type", "field_type": "dropdown", "action": "browser_select_option"},
            {"environment": "prodnci", "process": "retrieval", "tab_name": "Service Details", "section_name": "Footer", "field_name": "Contact Info", "field_type": "text", "action": "retrieve"},
            {"environment": "b3ft", "process": "filling", "tab_name": "Service Details", "section_name": "Footer", "field_name": "Contact Info", "field_type": "text", "action": "browser_type"},
            {"environment": "prodnci", "process": "retrieval", "tab_name": "Employer-General", "section_name": "General", "field_name": "City", "field_type": "textbox", "action": "retrieve"},
            {"environment": "b3ft", "process": "filling", "tab_name": "Employer-General", "section_name": "General", "field_name": "City", "field_type": "textbox", "action": "browser_type"},
            # Missing fields
            {"environment": None, "process": "retrieval", "tab_name": "Integrated_Program", "section_name": None, "field_name": "Department", "field_type": "textbox", "action": None},
            {"environment": "prodnci", "process": "retrieval", "tab_name": None, "section_name": "Employee Distribution", "field_name": "Headcount", "field_type": None, "action": "retrieve"},
            {"environment": None, "process": "filling", "tab_name": None, "section_name": "General", "field_name": "State", "field_type": "dropdown", "action": None},
        ],
        "Microsoft": [
            {"environment": "prodnci", "process": "retrieval", "tab_name": "Employer-General", "section_name": "General", "field_name": "Industry", "field_type": "dropdown", "action": "retrieve"},
            {"environment": "b3ft", "process": "filling", "tab_name": "Employer-General", "section_name": "General", "field_name": "Industry", "field_type": "dropdown", "action": "browser_select_option"},
            {"environment": "prodnci", "process": "retrieval", "tab_name": "Service Details", "section_name": "Footer", "field_name": "Privacy Policy", "field_type": "text", "action": "retrieve"},
            {"environment": "b3ft", "process": "filling", "tab_name": "Service Details", "section_name": "Footer", "field_name": "Privacy Policy", "field_type": "text", "action": "browser_type"},
            {"environment": "prodnci", "process": "retrieval", "tab_name": "Integrated_Program", "section_name": "Employee Distribution", "field_name": "Benefit Enrollment", "field_type": "radio_button", "action": "retrieve"},
            {"environment": "b3ft", "process": "filling", "tab_name": "Integrated_Program", "section_name": "Employee Distribution", "field_name": "Benefit Enrollment", "field_type": "radio_button", "action": "browser_click"},
            {"environment": "prodnci", "process": "retrieval", "tab_name": "Employer-General", "section_name": "General", "field_name": "Stock Symbol", "field_type": "text", "action": "retrieve"},
            # Missing fields
            {"environment": None, "process": "retrieval", "tab_name": "Employer-General", "section_name": "General", "field_name": "Tax ID", "field_type": None, "action": "retrieve"},
            {"environment": "prodnci", "process": "retrieval", "tab_name": None, "section_name": None, "field_name": "Registration Number", "field_type": "textbox", "action": None},
            {"environment": None, "process": "filling", "tab_name": "Service Details", "section_name": None, "field_name": "License", "field_type": "text", "action": None},
        ],
    }
    
    total_records = 0
    
    for customer_name in customer_names:
        if customer_name in sample_templates:
            for template in sample_templates[customer_name]:
                record = FromEnvironment(
                    request_id=request_id,
                    customer_name=customer_name,
                    **template
                )
                db.add(record)
                total_records += 1
    
    db.commit()
    return total_records

# --- FASTAPI APP ---
app = FastAPI(
    title="Environment Data Setup API",
    description="Setup and manage environment data",
    version="1.0.0"
)

# --- API ENDPOINTS ---

@app.get("/")
async def root():
    return {
        "message": "Environment Data Setup API", 
        "status": "Running"
    }

@app.post("/add-data")
async def add_customer_data(request_id: int, customer_name: str):
    """Add sample data for a specific customer with a request_id"""
    
    valid_customers = ["IBM", "CITY OF ADELANTO", "Microsoft"]
    
    if customer_name not in valid_customers:
        raise HTTPException(
            status_code=400, 
            detail=f"Customer must be one of: {valid_customers}"
        )
    
    with get_db() as db:
        # Check if data already exists for this request_id and customer
        existing = db.query(FromEnvironment).filter(
            FromEnvironment.request_id == request_id,
            FromEnvironment.customer_name == customer_name
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Data already exists for request_id={request_id} and customer={customer_name}"
            )
        
        total_records = populate_sample_data_for_customers(request_id, [customer_name], db)
        
        return {
            "message": f"Successfully added data for {customer_name}",
            "request_id": request_id,
            "customer_name": customer_name,
            "total_records": total_records
        }

@app.get("/view-data")
async def view_all_data():
    """View all records in from_environment table"""
    
    with get_db() as db:
        records = db.query(FromEnvironment).all()
        return {
            "total_records": len(records),
            "records": [
                {
                    "id": r.id,
                    "request_id": r.request_id,
                    "customer_name": r.customer_name,
                    "environment": r.environment,
                    "process": r.process,
                    "tab_name": r.tab_name,
                    "section_name": r.section_name,
                    "field_name": r.field_name,
                    "field_type": r.field_type,
                    "action": r.action
                }
                for r in records
            ]
        }

@app.get("/view-data/{request_id}")
async def view_data_by_request(request_id: int):
    """View data for a specific request_id"""
    
    with get_db() as db:
        records = db.query(FromEnvironment).filter(
            FromEnvironment.request_id == request_id
        ).all()
        
        if not records:
            raise HTTPException(status_code=404, detail="No data found for this request_id")
        
        return {
            "request_id": request_id,
            "total_records": len(records),
            "records": [
                {
                    "id": r.id,
                    "customer_name": r.customer_name,
                    "environment": r.environment,
                    "process": r.process,
                    "tab_name": r.tab_name,
                    "section_name": r.section_name,
                    "field_name": r.field_name,
                    "field_type": r.field_type,
                    "action": r.action
                }
                for r in records
            ]
        }

@app.post("/add-all-sample-data")
async def add_all_sample_data():
    """Add sample data for all customers (IBM, CITY OF ADELANTO, Microsoft) with sequential request_ids"""
    
    customers = ["IBM", "CITY OF ADELANTO", "Microsoft"]
    
    with get_db() as db:
        # Check if any data already exists
        existing_count = db.query(FromEnvironment).count()
        
        if existing_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Data already exists in the table ({existing_count} records). Use /clear-all first to reset."
            )
        
        total_records = 0
        results = []
        
        for idx, customer_name in enumerate(customers, start=1):
            request_id = idx
            records_added = populate_sample_data_for_customers(request_id, [customer_name], db)
            total_records += records_added
            
            results.append({
                "request_id": request_id,
                "customer_name": customer_name,
                "records_added": records_added
            })
        
        return {
            "message": "Successfully added sample data for all customers",
            "total_records": total_records,
            "details": results
        }

@app.delete("/clear-all")
async def clear_all_data():
    """Clear all data from from_environment table"""
    
    with get_db() as db:
        count = db.query(FromEnvironment).count()
        db.query(FromEnvironment).delete()
        db.commit()
        
        return {
            "message": "All data cleared",
            "records_deleted": count
        }

if __name__ == "__main__":
    uvicorn.run("DBC1:app", host="0.0.0.0", port=8000)