#!/usr/bin/env python3
"""
Batch upload test invoices to demonstrate intelligent routing.
"""
import requests
import time
from pathlib import Path

# Configuration
API_BASE_URL = "https://asp-adl-m365-us-baaydcahbudkeef8.westus3-01.azurewebsites.net"
# API_BASE_URL = "http://127.0.0.1:8000"  # Use this for local testing

def upload_invoice(file_path: Path, confidence_threshold: float = 0.85):
    """Upload an invoice and show the routing result"""
    url = f"{API_BASE_URL}/invoices/process"
    params = {"confidence_threshold": confidence_threshold}

    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "application/pdf")}
        response = requests.post(url, files=files, params=params)

    if response.status_code == 200:
        data = response.json()
        status = data["status"]
        confidence = data["invoice_data"]["confidence"]
        vendor = data["invoice_data"]["vendor"]
        invoice_num = data["invoice_data"]["invoice_number"]

        if status == "auto_approved":
            print(f"✅ AUTO-APPROVED: {vendor} - {invoice_num} (confidence: {confidence:.1%})")
        else:
            print(f"📧 SENT TO TEAMS: {vendor} - {invoice_num} (confidence: {confidence:.1%})")

        return data
    else:
        print(f"❌ ERROR: {response.status_code} - {response.text}")
        return None


def main():
    print("=" * 70)
    print("Batch Invoice Upload Test - Intelligent Routing Demo")
    print("=" * 70)
    print()

    # Check if sample invoice exists
    sample_invoice = Path("/tmp/sample_invoice.pdf")

    if not sample_invoice.exists():
        print(f"⚠️  Sample invoice not found at {sample_invoice}")
        print("Downloading sample invoice...")

        # Download sample invoice
        import subprocess
        result = subprocess.run([
            "curl", "-L", "-o", str(sample_invoice),
            "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/sample-invoice.pdf"
        ], capture_output=True)

        if result.returncode == 0:
            print(f"✓ Downloaded sample invoice to {sample_invoice}")
        else:
            print("❌ Failed to download sample invoice")
            return

    print(f"Using invoice: {sample_invoice}")
    print(f"API Endpoint: {API_BASE_URL}")
    print()
    print("Uploading invoices with different confidence thresholds...")
    print("-" * 70)

    # Test 1: Upload with default threshold (0.85) - should auto-approve
    print("\n1. Upload with default threshold (0.85):")
    upload_invoice(sample_invoice, confidence_threshold=0.85)
    time.sleep(1)

    # Test 2: Upload with very high threshold (0.99) - should go to Teams
    print("\n2. Upload with high threshold (0.99) - force Teams review:")
    upload_invoice(sample_invoice, confidence_threshold=0.99)
    time.sleep(1)

    # Test 3: Upload with low threshold (0.50) - should auto-approve
    print("\n3. Upload with low threshold (0.50):")
    upload_invoice(sample_invoice, confidence_threshold=0.50)
    time.sleep(1)

    print("\n" + "-" * 70)
    print("\nFetching all approved invoices...")
    print("-" * 70)

    # Get approved invoices list
    response = requests.get(f"{API_BASE_URL}/invoices/approvals/approved")
    if response.status_code == 200:
        data = response.json()
        print(f"\nTotal Approved: {data['total_approved']}")
        print()

        for invoice in data["invoices"]:
            approval_type = invoice["approval_type"]
            icon = "🤖" if "AI" in approval_type else "👤"
            print(f"{icon} {approval_type}")
            print(f"   Vendor: {invoice['vendor']}")
            print(f"   Invoice #: {invoice['invoice_number']}")
            print(f"   Total: {invoice['currency']} {invoice['total']}")
            print(f"   Confidence: {invoice['confidence']:.1%}")
            print(f"   Approved: {invoice['approved_at']}")
            print()

    print("=" * 70)
    print("Test Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
