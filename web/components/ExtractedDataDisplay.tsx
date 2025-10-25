
import React from 'react';

interface ExtractedData {
  // Define the structure of your extracted data here
  // For example:
  invoiceId: string;
  customerName: string;
  totalAmount: number;
  // ... and so on
}

interface ExtractedDataDisplayProps {
  data: ExtractedData | null;
}

const ExtractedDataDisplay: React.FC<ExtractedDataDisplayProps> = ({ data }) => {
  if (!data) {
    return null;
  }

  return (
    <div className="mt-8 p-4 border rounded-lg bg-gray-50">
      <h2 className="text-2xl font-bold mb-4">Extracted Data</h2>
      <div>
        <p><strong>Invoice ID:</strong> {data.invoiceId}</p>
        <p><strong>Customer Name:</strong> {data.customerName}</p>
        <p><strong>Total Amount:</strong> {data.totalAmount}</p>
        {/* Add more fields as needed */}
      </div>
    </div>
  );
};

export default ExtractedDataDisplay;
