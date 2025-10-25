'use client';

import React, { useState, useCallback } from 'react';
import DragDropArea from '../../components/DragDropArea';
import ExtractedDataDisplay from '../../components/ExtractedDataDisplay';
import ThemeToggle from '../../components/ThemeToggle';

interface ExtractedData {
  vendor: string;
  invoice_number: string;
  invoice_date: string;
  total: number;
  currency: string;
  confidence: number;
  content: string;
  bill_to: string;
}

interface ValidationResult {
  approved: boolean;
  reason: string;
  checks: {
    amount_within_limit: boolean;
    confidence_sufficient: boolean;
    document_type_is_invoice: boolean;
    document_type_not_receipt: boolean;
    bill_to_authorized: boolean;
  };
  metadata: {
    amount: number;
    confidence: number;
    vendor: string;
    config: {
      amount_threshold: number;
      min_confidence: number;
      require_invoice_keyword: boolean;
      reject_receipt_keyword: boolean;
    };
  };
}

const UploadPage: React.FC = () => {
  const [acceptedFiles, setAcceptedFiles] = useState<File[]>([]);
  const [extractedData, setExtractedData] = useState<ExtractedData | null>(null);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authorizedCompanies, setAuthorizedCompanies] = useState<string>('My Company Pty Ltd, Acme Corporation');

  const handleFilesAccepted = useCallback(async (files: File[]) => {
    if (files.length === 0) return;

    setAcceptedFiles(files);
    setLoading(true);
    setError(null);
    setExtractedData(null);
    setValidationResult(null);

    try {
      const file = files[0]; // Process first file only
      const formData = new FormData();
      formData.append('file', file);

      // Step 1: Call FastAPI extraction endpoint
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const extractResponse = await fetch(`${apiUrl}/invoices/extract`, {
        method: 'POST',
        body: formData,
      });

      if (!extractResponse.ok) {
        throw new Error(`Extraction failed: ${extractResponse.statusText}`);
      }

      const extractedData = await extractResponse.json();
      setExtractedData(extractedData);
      setLoading(false);

      // Step 2: Call FastAPI validation endpoint
      setValidating(true);

      // Parse comma-separated company names and trim whitespace
      const companiesList = authorizedCompanies
        .split(',')
        .map(c => c.trim())
        .filter(c => c.length > 0);

      const validateResponse = await fetch(`${apiUrl}/invoices/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          amount: extractedData.total,
          confidence: extractedData.confidence,
          content: extractedData.content || '',  // Full OCR text from Azure DI
          vendor: extractedData.vendor,
          bill_to: extractedData.bill_to,
          bill_to_authorized: companiesList,
        }),
      });

      if (!validateResponse.ok) {
        throw new Error(`Validation failed: ${validateResponse.statusText}`);
      }

      const validationData = await validateResponse.json();
      setValidationResult(validationData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
      setValidating(false);
    }
  }, [authorizedCompanies]);

  return (
    <div className="page-container">
      <header className="page-header">
        <div className="page-header-content">
          <div>
            <h1>Invoice Document Intelligence</h1>
            <p className="page-subtitle">
              Upload an invoice PDF to extract fields using Azure Document Intelligence
            </p>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="page-main">
        <div className="page-grid">
          {/* Left column: Upload and extraction */}
          <section className="page-section" aria-labelledby="upload-heading">
            <h2 id="upload-heading" className="section-heading">Upload</h2>

            <div className="form-group">
              <label htmlFor="authorizedCompanies" className="form-label">
                Authorized Companies
              </label>
              <input
                id="authorizedCompanies"
                type="text"
                value={authorizedCompanies}
                onChange={(e) => setAuthorizedCompanies(e.target.value)}
                className="form-input"
                placeholder="e.g., My Company Pty Ltd, Acme Corporation"
                aria-describedby="companies-help"
              />
              <p id="companies-help" className="form-help">
                Comma-separated list. Invoices to other companies require manual approval
              </p>
            </div>

            <DragDropArea onFilesAccepted={handleFilesAccepted} />

            {acceptedFiles.length > 0 && (
              <div className="status-card status-info" role="status">
                <div className="status-icon" aria-hidden="true">ℹ</div>
                <div>
                  <p className="status-title">File Selected</p>
                  <p className="status-text">
                    {acceptedFiles[0].name} ({(acceptedFiles[0].size / 1024).toFixed(2)} KB)
                  </p>
                </div>
              </div>
            )}

            {loading && (
              <div className="status-card status-info" role="status" aria-live="polite">
                <div className="status-icon status-icon-spin" aria-hidden="true">⟳</div>
                <div>
                  <p className="status-title">Processing</p>
                  <p className="status-text">Extracting data with Azure Document Intelligence...</p>
                </div>
              </div>
            )}

            {validating && (
              <div className="status-card status-info" role="status" aria-live="polite">
                <div className="status-icon status-icon-spin" aria-hidden="true">⟳</div>
                <div>
                  <p className="status-title">Validating</p>
                  <p className="status-text">Checking invoice against approval rules...</p>
                </div>
              </div>
            )}

            {error && (
              <div className="status-card status-error" role="alert" aria-live="assertive">
                <div className="status-icon" aria-hidden="true">✗</div>
                <div>
                  <p className="status-title">Error</p>
                  <p className="status-text">{error}</p>
                </div>
              </div>
            )}
          </section>

          {/* Right column: Extracted data and decision */}
          <section className="page-section" aria-labelledby="results-heading">
            <h2 id="results-heading" className="section-heading">Results</h2>

            {!extractedData && !loading && !error && (
              <div className="empty-state">
                <div className="empty-state-icon" aria-hidden="true">📄</div>
                <h3 className="empty-state-title">No Invoice Uploaded</h3>
                <p className="empty-state-text">
                  Upload an invoice PDF to see extracted data and validation results
                </p>
              </div>
            )}

            {extractedData && (
              <ExtractedDataDisplay data={extractedData} validation={validationResult} />
            )}
          </section>
        </div>
      </main>
    </div>
  );
};

export default UploadPage;