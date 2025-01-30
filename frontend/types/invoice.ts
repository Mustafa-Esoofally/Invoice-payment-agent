export interface InvoiceData {
  invoice_number: string;
  amount: number;
  currency: string;
  due_date: string;
  recipient: string;
  description: string;
  file_name: string;
  bank_details: {
    account_name: string;
    account_number: string;
    routing_number: string;
    bank_name: string;
    account_type: string;
  };
  metadata: {
    invoice_date: string;
    payment_terms: string;
    po_number: string;
    tax_amount: number;
    subtotal: number;
  };
}

export interface Invoice {
  id: string;
  status: string;
  created_at: string;
  customer_id: string;
  data: InvoiceData;
  source: string;
}

export interface ScanInboxResponse {
  success: boolean;
  message: string;
  existing_invoices: Invoice[];
  new_invoices: Invoice[];
  summary: {
    total_invoices: number;
    existing_count: number;
    new_count: number;
    total_amount: number;
  };
} 