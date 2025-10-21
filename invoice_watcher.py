#!/usr/bin/env python3
"""
Invoice Folder Watcher - Automatic Processing Demo

Watches a folder for new invoice files and automatically processes them
through the intelligent routing API. Simulates SharePoint + Power Automate workflow.

Usage:
    python invoice_watcher.py --watch-folder ./invoices-incoming
"""

import argparse
import time
import requests
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import json

# Configuration
API_BASE_URL = "https://asp-adl-m365-us-baaydcahbudkeef8.westus3-01.azurewebsites.net"
CONFIDENCE_THRESHOLD = 0.85

class InvoiceHandler(FileSystemEventHandler):
    """Handles new invoice file events"""

    def __init__(self, watch_folder, processed_folder, pending_folder):
        self.watch_folder = Path(watch_folder)
        self.processed_folder = Path(processed_folder)
        self.pending_folder = Path(pending_folder)
        self.processed_files = set()

        # Create folders if they don't exist
        self.processed_folder.mkdir(exist_ok=True)
        self.pending_folder.mkdir(exist_ok=True)

    def on_created(self, event):
        """Called when a file is created in the watched folder"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process PDF files
        if file_path.suffix.lower() != '.pdf':
            return

        # Avoid processing the same file multiple times
        if file_path in self.processed_files:
            return

        # Small delay to ensure file is fully written
        time.sleep(1)

        # Check if file still exists (might have been moved)
        if not file_path.exists():
            return

        self.processed_files.add(file_path)
        self.process_invoice(file_path)

    def process_invoice(self, file_path: Path):
        """Process an invoice through the API"""
        print("\n" + "="*70)
        print(f"📄 NEW INVOICE DETECTED: {file_path.name}")
        print("="*70)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Size: {file_path.stat().st_size:,} bytes")
        print()

        try:
            # Upload to API
            print("🔄 Uploading to API...")
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, 'application/pdf')}
                params = {'confidence_threshold': CONFIDENCE_THRESHOLD}

                response = requests.post(
                    f"{API_BASE_URL}/invoices/process",
                    files=files,
                    params=params,
                    timeout=120
                )

            if response.status_code == 200:
                data = response.json()
                self.handle_success(file_path, data)
            else:
                print(f"❌ API Error: {response.status_code}")
                print(f"   {response.text}")
                self.handle_error(file_path, f"API returned {response.status_code}")

        except requests.exceptions.Timeout:
            print("⏱️  Request timed out (Azure DI processing can take 30+ seconds)")
            self.handle_error(file_path, "Timeout")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.handle_error(file_path, str(e))

    def handle_success(self, file_path: Path, data: dict):
        """Handle successful processing"""
        status = data['status']
        invoice_data = data['invoice_data']

        print()
        print("📊 EXTRACTION RESULTS:")
        print(f"   Vendor: {invoice_data['vendor']}")
        print(f"   Invoice #: {invoice_data['invoice_number']}")
        print(f"   Date: {invoice_data['invoice_date']}")
        print(f"   Total: {invoice_data['currency']} {invoice_data['total']}")
        print(f"   Confidence: {invoice_data['confidence']:.1%}")
        print()

        if status == 'auto_approved':
            print("✅ RESULT: AUTO-APPROVED BY AI")
            print("   → Invoice automatically approved")
            print("   → Ready for ERP integration")
            destination = self.processed_folder
            status_emoji = "✅"
        else:
            print("📧 RESULT: SENT TO TEAMS FOR REVIEW")
            print("   → Confidence below threshold")
            print("   → Awaiting human approval")
            destination = self.pending_folder
            status_emoji = "⏳"

        # Move file to appropriate folder
        dest_path = destination / f"{status_emoji}_{file_path.name}"
        file_path.rename(dest_path)
        print(f"\n📁 Moved to: {dest_path}")

        # Log to JSON
        self.log_processing(file_path.name, data, dest_path)

        print("="*70)

    def handle_error(self, file_path: Path, error_msg: str):
        """Handle processing error"""
        print(f"\n❌ Processing failed: {error_msg}")

        # Move to pending for manual review
        dest_path = self.pending_folder / f"ERROR_{file_path.name}"
        file_path.rename(dest_path)
        print(f"📁 Moved to: {dest_path}")
        print("="*70)

    def log_processing(self, filename: str, data: dict, dest_path: Path):
        """Log processing results to JSON file"""
        log_file = self.watch_folder.parent / "processing_log.json"

        # Load existing log
        if log_file.exists():
            with open(log_file, 'r') as f:
                log_data = json.load(f)
        else:
            log_data = []

        # Add new entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "filename": filename,
            "status": data['status'],
            "invoice_data": data['invoice_data'],
            "approval_id": data.get('approval_id'),
            "destination": str(dest_path)
        }
        log_data.append(log_entry)

        # Save log
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Watch a folder for invoices and process them automatically'
    )
    parser.add_argument(
        '--watch-folder',
        default='./invoices-incoming',
        help='Folder to watch for new invoices (default: ./invoices-incoming)'
    )
    parser.add_argument(
        '--processed-folder',
        default='./invoices-processed',
        help='Folder for auto-approved invoices (default: ./invoices-processed)'
    )
    parser.add_argument(
        '--pending-folder',
        default='./invoices-pending',
        help='Folder for pending approvals (default: ./invoices-pending)'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.85,
        help='Confidence threshold (default: 0.85)'
    )
    parser.add_argument(
        '--api-url',
        default=API_BASE_URL,
        help=f'API base URL (default: {API_BASE_URL})'
    )

    args = parser.parse_args()

    # Update global config
    global API_BASE_URL, CONFIDENCE_THRESHOLD
    API_BASE_URL = args.api_url
    CONFIDENCE_THRESHOLD = args.threshold

    # Create watch folder
    watch_folder = Path(args.watch_folder)
    watch_folder.mkdir(exist_ok=True)

    # Set up file watcher
    event_handler = InvoiceHandler(
        args.watch_folder,
        args.processed_folder,
        args.pending_folder
    )
    observer = Observer()
    observer.schedule(event_handler, str(watch_folder), recursive=False)
    observer.start()

    print("="*70)
    print("🔍 INVOICE WATCHER - AUTOMATIC PROCESSING")
    print("="*70)
    print(f"Watching: {watch_folder.absolute()}")
    print(f"Auto-Approved → {Path(args.processed_folder).absolute()}")
    print(f"Pending Review → {Path(args.pending_folder).absolute()}")
    print(f"API: {API_BASE_URL}")
    print(f"Confidence Threshold: {CONFIDENCE_THRESHOLD}")
    print()
    print("💡 Drop PDF invoices into the watch folder to process them")
    print("Press Ctrl+C to stop")
    print("="*70)
    print()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 Stopping watcher...")
        observer.stop()

    observer.join()
    print("✅ Watcher stopped")


if __name__ == "__main__":
    main()
