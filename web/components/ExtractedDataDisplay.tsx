import React from 'react';

interface ExtractedData {
  vendor: string;
  invoice_number: string;
  invoice_date: string;
  total: number;
  currency: string;
  confidence: number;
  bill_to?: string;
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

interface ExtractedDataDisplayProps {
  data: ExtractedData | null;
  validation: ValidationResult | null;
}

const ConfidenceBadge: React.FC<{ confidence: number }> = ({ confidence }) => {
  const percentage = (confidence * 100).toFixed(1);
  let statusClass = 'badge-error';
  let icon = '✗';

  if (confidence >= 0.85) {
    statusClass = 'badge-success';
    icon = '✓';
  } else if (confidence >= 0.7) {
    statusClass = 'badge-warning';
    icon = '⚠';
  }

  return (
    <span className={`badge ${statusClass}`} role="status">
      <span aria-hidden="true">{icon}</span>
      {percentage}% confidence
    </span>
  );
};

const CheckIcon: React.FC<{ passed: boolean }> = ({ passed }) => {
  return (
    <span className={`check-icon ${passed ? 'check-icon-pass' : 'check-icon-fail'}`} aria-hidden="true">
      {passed ? '✓' : '✗'}
    </span>
  );
};

const ExtractedDataDisplay: React.FC<ExtractedDataDisplayProps> = ({ data, validation }) => {
  if (!data) {
    return null;
  }

  return (
    <div className="results-container">
      {/* Extraction Results */}
      <section className="result-card" aria-labelledby="extraction-heading">
        <div className="result-card-header">
          <h3 id="extraction-heading" className="result-card-title">
            <span className="check-icon check-icon-pass" aria-hidden="true">✓</span>
            Extraction Complete
          </h3>
          <ConfidenceBadge confidence={data.confidence} />
        </div>

        <div className="data-grid">
          <div className="data-field">
            <label className="data-label">Document Type</label>
            <p className="data-value">Invoice</p>
            <p className="data-help">Verified by Azure Document Intelligence</p>
          </div>

          <div className="data-field">
            <label className="data-label">Invoice Number</label>
            <p className="data-value">{data.invoice_number || 'Not found'}</p>
          </div>

          <div className="data-field">
            <label className="data-label">Vendor</label>
            <p className="data-value">{data.vendor || 'Unknown'}</p>
          </div>

          <div className="data-field">
            <label className="data-label">Bill To</label>
            <p className="data-value">{data.bill_to || 'Not found'}</p>
          </div>

          <div className="data-field">
            <label className="data-label">Invoice Date</label>
            <p className="data-value">{data.invoice_date || 'Not found'}</p>
          </div>

          <div className="data-field">
            <label className="data-label">Total Amount</label>
            <p className="data-value data-value-large">
              {data.currency} {data.total.toFixed(2)}
            </p>
          </div>

          <div className="data-field">
            <label className="data-label">Overall Confidence</label>
            <div className="confidence-bar">
              <div
                className={`confidence-bar-fill ${
                  data.confidence >= 0.85 ? 'confidence-bar-success' :
                  data.confidence >= 0.7 ? 'confidence-bar-warning' : 'confidence-bar-error'
                }`}
                style={{ width: `${data.confidence * 100}%` }}
                role="progressbar"
                aria-valuenow={data.confidence * 100}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label="Confidence level"
              />
            </div>
            <span className="confidence-text">{(data.confidence * 100).toFixed(1)}%</span>
          </div>
        </div>
      </section>

      {/* Validation Results */}
      {validation && (
        <section
          className={`result-card ${validation.approved ? 'result-card-success' : 'result-card-warning'}`}
          aria-labelledby="decision-heading"
          role="region"
          aria-live="polite"
        >
          <div className="result-card-header">
            <h3 id="decision-heading" className="result-card-title">
              {validation.approved ? (
                <>
                  <span className="check-icon check-icon-pass" aria-hidden="true">✓</span>
                  Approved
                </>
              ) : (
                <>
                  <span className="check-icon check-icon-warn" aria-hidden="true">⚠</span>
                  Requires Manual Review
                </>
              )}
            </h3>
          </div>

          <div className="validation-content">
            <div className="validation-section">
              <h4 className="validation-heading">Decision Reason</h4>
              <p className="validation-text">{validation.reason}</p>
            </div>

            <div className="validation-section">
              <h4 className="validation-heading">Validation Checks</h4>
              <div className="checks-list">
                <div className="check-item">
                  <CheckIcon passed={validation.checks.amount_within_limit} />
                  <span className="check-label">
                    Amount ≤ ${validation.metadata.config.amount_threshold.toFixed(0)}
                  </span>
                  <span className="check-detail">
                    (Invoice: ${validation.metadata.amount.toFixed(2)})
                  </span>
                </div>

                <div className="check-item">
                  <CheckIcon passed={validation.checks.confidence_sufficient} />
                  <span className="check-label">
                    Confidence ≥ {(validation.metadata.config.min_confidence * 100).toFixed(0)}%
                  </span>
                  <span className="check-detail">
                    (Actual: {(validation.metadata.confidence * 100).toFixed(1)}%)
                  </span>
                </div>

                <div className="check-item">
                  <CheckIcon passed={validation.checks.document_type_is_invoice} />
                  <span className="check-label">
                    Payment obligation detected
                  </span>
                  <span className="check-detail">
                    (analyzed: due dates, remittance terms, banking info)
                  </span>
                </div>

                <div className="check-item">
                  <CheckIcon passed={validation.checks.document_type_not_receipt} />
                  <span className="check-label">
                    Not a payment confirmation
                  </span>
                  <span className="check-detail">
                    (checked: receipt indicators, paid status, card details)
                  </span>
                </div>

                <div className="check-item">
                  <CheckIcon passed={validation.checks.bill_to_authorized} />
                  <span className="check-label">
                    Invoice addressed to authorized company
                  </span>
                  <span className="check-detail">
                    (security: prevents fraud and misdirected invoices)
                  </span>
                </div>
              </div>
            </div>

            <div className="validation-section">
              <h4 className="validation-subheading">Intelligent Document Classification</h4>
              <p className="validation-help">
                Our system analyzes payment obligation intent by examining:
                <strong> obligation cues</strong> (amount due, remittance instructions, due dates),
                <strong> confirmation cues</strong> (payment received, card details, zero balance), and
                <strong> contextual indicators</strong> (banking info, payment terms).
                This mimics how AP clerks determine: &quot;Does this require payment action?&quot;
              </p>
            </div>

            <div className="decision-summary">
              {validation.approved ? (
                <span className="decision-summary-success">
                  <span aria-hidden="true">✓</span> This invoice meets all approval criteria and can be processed automatically.
                </span>
              ) : (
                <span className="decision-summary-warning">
                  <span aria-hidden="true">⚠</span> This invoice requires manual review before approval.
                </span>
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  );
};

export default ExtractedDataDisplay;
