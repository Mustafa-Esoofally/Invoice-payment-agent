"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Mail, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "@/components/ui/use-toast";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ProfileDetails } from "@/components/ProfileDetails";
import { PaymentHistory } from "@/components/PaymentHistory";
import { ProcessInvoices } from "@/components/ProcessInvoices";
import { InvoiceList } from "@/components/InvoiceList";
import { Invoice, ScanInboxResponse } from "@/types/invoice";
import { createAuthHeader } from "@/lib/utils";

interface EmailProfile {
  emailAddress: string;
  displayName: string;
  status: string;
  profileData?: {
    emailAddress: string;
    messagesTotal?: number;
    threadsTotal?: number;
    historyId?: string;
  };
}

interface PaymentHistory {
  email: {
    subject: string;
    sender: string;
    timestamp: string;
  };
  invoice: {
    invoice_number: string;
    paid_amount: number;
    recipient: string;
    date: string;
    due_date: string;
  };
  payment: {
    success: boolean;
    amount: number;
    recipient: string;
    reference: string | null;
    error: string | null;
  };
  timestamp: string;
}

export default function Home() {
  const [isScanning, setIsScanning] = useState(false);
  const [existingInvoices, setExistingInvoices] = useState<Invoice[]>([]);
  const [newInvoices, setNewInvoices] = useState<Invoice[]>([]);
  const [paymentHistory, setPaymentHistory] = useState<PaymentHistory[]>([]);

  const fetchPaymentHistory = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/payment-history', {
        headers: createAuthHeader(),
      });
      if (!response.ok) throw new Error('Failed to fetch payment history');
      
      const data = await response.json();
      setPaymentHistory(data.payments);
    } catch (error) {
      console.error('Failed to fetch payment history:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to fetch payment history",
      });
    }
  }, []);

  const handleScanInbox = useCallback(async () => {
    try {
      setIsScanning(true);
      const response = await fetch('http://localhost:8000/scan-inbox', {
        method: 'POST',
        headers: createAuthHeader(),
        body: JSON.stringify({
          max_results: 10
        })
      });

      if (!response.ok) {
        throw new Error('Failed to scan inbox');
      }

      const data = await response.json();
      
      // Transform the backend invoices to match our frontend interface
      const transformedInvoices: Invoice[] = data.invoices.map((invoice: any) => ({
        id: invoice.id || String(Math.random()),
        status: invoice.status || 'pending',
        created_at: invoice.created_at || new Date().toISOString(),
        customer_id: invoice.customer_id || '',
        source: invoice.source || 'email',
        data: {
          invoice_number: invoice.invoice_number || '',
          amount: invoice.amount || 0,
          currency: invoice.currency || 'USD',
          due_date: invoice.due_date || new Date().toISOString(),
          recipient: invoice.recipient || '',
          description: invoice.description || '',
          file_name: invoice.file_name || '',
          bank_details: {
            account_name: invoice.bank_details?.account_name || '',
            account_number: invoice.bank_details?.account_number || '',
            routing_number: invoice.bank_details?.routing_number || '',
            bank_name: invoice.bank_details?.bank_name || '',
            account_type: invoice.bank_details?.account_type || '',
          },
          metadata: {
            invoice_date: invoice.metadata?.invoice_date || new Date().toISOString(),
            payment_terms: invoice.metadata?.payment_terms || '',
            po_number: invoice.metadata?.po_number || '',
            tax_amount: invoice.metadata?.tax_amount || 0,
            subtotal: invoice.metadata?.subtotal || 0,
          }
        }
      }));

      const transformedData: ScanInboxResponse = {
        success: data.success,
        message: data.message,
        existing_invoices: transformedInvoices,
        new_invoices: [], // Backend doesn't differentiate between new and existing yet
        summary: {
          total_invoices: data.summary.total_invoices,
          existing_count: data.summary.total_invoices,
          new_count: 0,
          total_amount: data.summary.total_amount
        }
      };

      setExistingInvoices(transformedData.existing_invoices);
      setNewInvoices(transformedData.new_invoices);

      toast({
        title: "Scan Complete",
        description: `Found ${transformedData.summary.total_invoices} invoices (Total: ${formatCurrency(transformedData.summary.total_amount)})`,
      });
    } catch (error) {
      console.error('Failed to scan inbox:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to scan inbox",
      });
    } finally {
      setIsScanning(false);
    }
  }, []);

  const handlePaymentComplete = useCallback(() => {
    // Refresh both invoice list and payment history
    handleScanInbox();
    fetchPaymentHistory();
  }, [handleScanInbox, fetchPaymentHistory]);

  const successCount = paymentHistory.filter(payment => payment.payment.success).length;
  const failedCount = paymentHistory.filter(payment => !payment.payment.success).length;

  return (
    <div className="min-h-screen bg-gray-50/50">
      <div className="container py-8 px-4">
        <div className="w-full max-w-5xl mx-auto space-y-6">
          <div className="text-center space-y-2">
            <h1 className="text-3xl font-bold tracking-tight">Invoice Payment Agent</h1>
            <p className="text-lg text-gray-600">Process your invoice emails automatically</p>
          </div>

          <Button 
            className="w-full bg-black hover:bg-gray-800"
            onClick={handleScanInbox}
            disabled={isScanning}
          >
            {isScanning ? 'Scanning Inbox...' : 'Scan Inbox'}
          </Button>

          {existingInvoices.length > 0 && (
            <InvoiceList 
              invoices={existingInvoices} 
              title="Existing Invoices" 
              onPaymentComplete={handlePaymentComplete}
            />
          )}

          {newInvoices.length > 0 && (
            <InvoiceList 
              invoices={newInvoices} 
              title="New Invoices" 
              onPaymentComplete={handlePaymentComplete}
            />
          )}

          {paymentHistory.length > 0 && (
            <PaymentHistory 
              payments={paymentHistory}
              successCount={successCount}
              failedCount={failedCount}
            />
          )}
        </div>
      </div>
    </div>
  );
}
