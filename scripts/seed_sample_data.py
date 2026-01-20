#!/usr/bin/env python3
"""Script to seed sample tables with realistic data for import/export operations."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.config import get_settings
from app.infrastructure.db.database import Database
from app.infrastructure.db.models import (
    SampleBillModel,
    SampleInvoiceModel,
    SampleProjectModel,
    SampleVendorModel,
)

logger = get_logger(__name__)
settings = get_settings()

# Default client IDs
DEFAULT_CLIENT_ID = UUID("00000000-0000-0000-0000-000000000000")
CLIENT_2_ID = UUID("11111111-1111-1111-1111-111111111111")


def generate_vendor_data(client_id: UUID, index: int) -> dict:
    """Generate realistic vendor data."""
    vendor_names = [
        "Acme Corporation",
        "Tech Solutions Inc",
        "Global Supplies Ltd",
        "Premier Services Co",
        "Advanced Systems Group",
        "Elite Manufacturing",
        "Proactive Solutions",
        "Innovative Technologies",
        "Strategic Partners LLC",
        "Quality Products Inc",
        "Reliable Services Corp",
        "Dynamic Solutions",
        "Prime Suppliers",
        "Excellence Industries",
        "Top Tier Vendors",
        "Best Value Co",
        "Premium Services",
        "Core Business Solutions",
        "Enterprise Partners",
        "Master Suppliers",
    ]
    
    company_types = ["Corp", "Inc", "LLC", "Ltd", "Co", "Group"]
    domains = ["com", "net", "org", "io", "co"]
    
    name = vendor_names[index % len(vendor_names)]
    domain_base = name.lower().replace(" ", "").replace(".", "").replace(",", "")
    email = f"contact@{domain_base}.{domains[index % len(domains)]}"
    phone = f"+1-555-{1000 + index:04d}"
    
    return {
        "id": uuid4(),
        "client_id": client_id,
        "name": name,
        "email_address": email,
        "phone": phone,
        "tax_number": f"TAX-{100000 + index:06d}",
        "is_supplier": True,
        "is_customer": index % 3 == 0,  # Some vendors are also customers
        "status": "ACTIVE" if index < 18 else "ARCHIVED",
        "currency": "USD",
        "address": {
            "street_1": f"{100 + index} Business St",
            "street_2": f"Suite {index % 10 + 1}" if index % 2 == 0 else None,
            "city": ["New York", "San Francisco", "Chicago", "Boston", "Seattle"][index % 5],
            "state": ["NY", "CA", "IL", "MA", "WA"][index % 5],
            "zip_code": f"{10000 + index:05d}",
            "country": "US",
        },
        "phone_numbers": [
            {"number": phone, "type": "WORK"},
            {"number": f"+1-555-{2000 + index:04d}", "type": "MOBILE"} if index % 2 == 0 else None,
        ],
        "created_at": datetime.now(UTC).replace(tzinfo=None) - timedelta(days=365 - index * 10),
        "updated_at": datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30 - index),
    }


def generate_project_data(client_id: UUID, index: int) -> dict:
    """Generate realistic project data."""
    project_names = [
        "Project Alpha",
        "Project Beta",
        "Project Gamma",
        "Project Delta",
        "Project Echo",
        "Project Foxtrot",
        "Project Golf",
        "Project Hotel",
        "Project India",
        "Project Juliet",
        "Project Kilo",
        "Project Lima",
        "Project Mike",
        "Project November",
        "Project Oscar",
        "Project Papa",
        "Project Quebec",
        "Project Romeo",
        "Project Sierra",
        "Project Tango",
    ]
    
    descriptions = [
        "Main development project",
        "Client engagement initiative",
        "Infrastructure upgrade",
        "Product launch campaign",
        "Research and development",
        "Marketing expansion",
        "Operations improvement",
        "Customer acquisition",
        "Revenue growth initiative",
        "Cost optimization project",
    ]
    
    statuses = ["active", "active", "active", "active", "completed", "cancelled", "on_hold"]
    
    start_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=180 - index * 5)
    end_date = start_date + timedelta(days=90 + index * 10) if index % 3 != 0 else None
    
    return {
        "id": uuid4(),
        "client_id": client_id,
        "code": f"PROJ-{index + 1:03d}",
        "name": project_names[index % len(project_names)],
        "description": descriptions[index % len(descriptions)],
        "status": statuses[index % len(statuses)],
        "start_date": start_date,
        "end_date": end_date,
        "budget": Decimal(f"{10000 + index * 5000}.00"),
        "currency": "USD",
        "created_at": start_date - timedelta(days=10),
        "updated_at": datetime.now(UTC).replace(tzinfo=None) - timedelta(days=index),
    }


def generate_bill_data(
    client_id: UUID, index: int, vendor_ids: list[UUID], project_ids: list[UUID]
) -> dict:
    """Generate realistic bill data."""
    descriptions = [
        "Office supplies and equipment",
        "Software licenses and subscriptions",
        "Professional services",
        "Hardware and infrastructure",
        "Marketing and advertising",
        "Consulting services",
        "Travel and accommodation",
        "Training and development",
        "Utilities and facilities",
        "Legal and compliance",
        "Insurance premiums",
        "Maintenance and repairs",
        "Research and development",
        "Product development",
        "Customer support tools",
    ]
    
    statuses = ["pending", "pending", "paid", "paid", "overdue"]
    
    bill_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30 - index * 2)
    due_date = bill_date + timedelta(days=30)
    paid_on_date = (
        bill_date + timedelta(days=index % 30)
        if statuses[index % len(statuses)] == "paid"
        else None
    )
    
    amount = Decimal(f"{100 + index * 50}.{index % 100:02d}")
    
    return {
        "id": uuid4(),
        "client_id": client_id,
        "bill_number": f"BILL-{2024}{index + 1:04d}",
        "vendor_id": vendor_ids[index % len(vendor_ids)] if vendor_ids else None,
        "project_id": project_ids[index % len(project_ids)] if project_ids else None,
        "amount": amount,
        "date": bill_date,
        "due_date": due_date,
        "paid_on_date": paid_on_date,
        "description": descriptions[index % len(descriptions)],
        "currency": "USD",
        "status": statuses[index % len(statuses)],
        "line_items": [
            {
                "description": descriptions[index % len(descriptions)],
                "quantity": index % 10 + 1,
                "unit_price": float(amount / (index % 10 + 1)),
                "total": float(amount),
            }
        ],
        "created_at": bill_date,
        "updated_at": datetime.now(UTC).replace(tzinfo=None) - timedelta(days=index),
    }


def generate_invoice_data(
    client_id: UUID, index: int, vendor_ids: list[UUID]
) -> dict:
    """Generate realistic invoice data."""
    memos = [
        "Consulting services for Q1",
        "Product development services",
        "Monthly retainer fee",
        "Project milestone payment",
        "Recurring subscription",
        "One-time implementation fee",
        "Support and maintenance",
        "Custom development work",
        "Training and onboarding",
        "Integration services",
    ]
    
    statuses = ["DRAFT", "SUBMITTED", "PAID", "PAID", "OVERDUE"]
    
    issue_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=45 - index * 2)
    due_date = issue_date + timedelta(days=30)
    paid_on_date = (
        issue_date + timedelta(days=index % 30)
        if statuses[index % len(statuses)] == "PAID"
        else None
    )
    
    sub_total = Decimal(f"{500 + index * 100}.00")
    tax_rate = Decimal("0.08")
    total_tax = sub_total * tax_rate
    total_amount = sub_total + total_tax
    balance = total_amount if statuses[index % len(statuses)] != "PAID" else Decimal("0.00")
    
    return {
        "id": uuid4(),
        "client_id": client_id,
        "invoice_number": f"INV-{2024}{index + 1:04d}",
        "contact_id": vendor_ids[index % len(vendor_ids)] if vendor_ids else None,
        "issue_date": issue_date,
        "due_date": due_date,
        "paid_on_date": paid_on_date,
        "memo": memos[index % len(memos)],
        "currency": "USD",
        "exchange_rate": Decimal("1.0000"),
        "sub_total": sub_total,
        "total_tax_amount": total_tax,
        "total_amount": total_amount,
        "balance": balance,
        "status": statuses[index % len(statuses)],
        "line_items": [
            {
                "description": memos[index % len(memos)],
                "quantity": index % 5 + 1,
                "unit_price": float(sub_total / (index % 5 + 1)),
                "total": float(sub_total),
            }
        ],
        "tracking_categories": [
            {"category": "Department", "value": ["Sales", "Engineering", "Marketing"][index % 3]}
        ],
        "created_at": issue_date,
        "updated_at": datetime.now(UTC).replace(tzinfo=None) - timedelta(days=index),
    }


async def seed_sample_data():
    """Seed sample tables with realistic data."""
    settings = get_settings()
    db = Database(
        settings.database_url,
        pool_size=5,
        max_overflow=10,
    )
    await db.connect()
    
    try:
        async with db.transaction() as session:
            # Check if data already exists
            result = await session.execute(select(SampleVendorModel).limit(1))
            if result.scalar_one_or_none():
                logger.info("Sample data already exists. Skipping seed.")
                return
            
            logger.info("Starting to seed sample data...")
            
            # Generate and insert vendors (20 for default client, 5 for client 2)
            logger.info("Creating vendors...")
            vendor_ids_default = []
            vendor_ids_client2 = []
            
            for i in range(20):
                vendor_data = generate_vendor_data(DEFAULT_CLIENT_ID, i)
                vendor = SampleVendorModel(**vendor_data)
                session.add(vendor)
                vendor_ids_default.append(vendor_data["id"])
            
            for i in range(5):
                vendor_data = generate_vendor_data(CLIENT_2_ID, i)
                vendor = SampleVendorModel(**vendor_data)
                session.add(vendor)
                vendor_ids_client2.append(vendor_data["id"])
            
            await session.commit()
            logger.info(f"Created {25} vendors")
            
            # Generate and insert projects (20 for default client, 5 for client 2)
            logger.info("Creating projects...")
            project_ids_default = []
            project_ids_client2 = []
            
            for i in range(20):
                project_data = generate_project_data(DEFAULT_CLIENT_ID, i)
                project = SampleProjectModel(**project_data)
                session.add(project)
                project_ids_default.append(project_data["id"])
            
            for i in range(5):
                project_data = generate_project_data(CLIENT_2_ID, i)
                project = SampleProjectModel(**project_data)
                session.add(project)
                project_ids_client2.append(project_data["id"])
            
            await session.commit()
            logger.info(f"Created {25} projects")
            
            # Generate and insert bills (20 for default client, 5 for client 2)
            logger.info("Creating bills...")
            for i in range(20):
                bill_data = generate_bill_data(
                    DEFAULT_CLIENT_ID, i, vendor_ids_default, project_ids_default
                )
                bill = SampleBillModel(**bill_data)
                session.add(bill)
            
            for i in range(5):
                bill_data = generate_bill_data(
                    CLIENT_2_ID, i, vendor_ids_client2, project_ids_client2
                )
                bill = SampleBillModel(**bill_data)
                session.add(bill)
            
            await session.commit()
            logger.info(f"Created {25} bills")
            
            # Generate and insert invoices (20 for default client, 5 for client 2)
            logger.info("Creating invoices...")
            for i in range(20):
                invoice_data = generate_invoice_data(DEFAULT_CLIENT_ID, i, vendor_ids_default)
                invoice = SampleInvoiceModel(**invoice_data)
                session.add(invoice)
            
            for i in range(5):
                invoice_data = generate_invoice_data(CLIENT_2_ID, i, vendor_ids_client2)
                invoice = SampleInvoiceModel(**invoice_data)
                session.add(invoice)
            
            await session.commit()
            logger.info(f"Created {25} invoices")
            
            logger.info("✅ Sample data seeding completed successfully!")
            logger.info(f"   - {25} vendors")
            logger.info(f"   - {25} projects")
            logger.info(f"   - {25} bills")
            logger.info(f"   - {25} invoices")
            
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(seed_sample_data())
