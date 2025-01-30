import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Invoice } from "@/types/invoice";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";
import { useState } from "react";
import { useToast } from "@/hooks/use-toast";
import { createAuthHeader } from "@/lib/utils";

interface InvoiceListProps {
  invoices: Invoice[];
  title: string;
  onPaymentComplete?: () => void;
}

interface PaymentResponse {
  success: boolean;
  message: string;
  invoice: {
    id: string;
    status: string;
    created_at: string;
    customer_id: string;
    metadata: {
      description: string;
      recipient: string;
      invoice_number: string;
      amount: number;
      invoice_date: string;
      due_date: string;
      bank_details: {
        bank_name: string;
        type: string;
        account_holder: string;
      };
    };
    payment_processing: {
      status: string;
      completed_at: string;
      payment_details: {
        amount: number;
        recipient: string;
        description: string;
        payment_id: string;
        payment_method: string;
        external_reference: string | null;
        transaction_details: {
          success: boolean;
          payment_method: string;
          invoice_number: string;
          payment_id: string;
        };
      };
    };
  };
  payment_details: {
    invoice_number: string;
    paid_amount: number;
    recipient: string;
    date: string;
    due_date: string;
    description: string;
    bank_details: {
      type: string;
      account_holder_name: string;
      account_number: string;
      bank_name: string;
    };
    customer: {
      name: string;
      email: string;
      phone: string;
      address: string;
    };
  };
  file: {
    name: string;
    path: string;
    processed: boolean;
  };
}

export function InvoiceList({ invoices, title, onPaymentComplete }: InvoiceListProps) {
  const [processingPayments, setProcessingPayments] = useState<Set<string>>(new Set());
  const { toast } = useToast();

  const handlePayInvoice = async (invoiceId: string) => {
    setProcessingPayments(prev => new Set(prev).add(invoiceId));
    
    try {
      const response = await fetch('http://localhost:8000/pay-invoice', {
        method: 'POST',
        headers: createAuthHeader(),
        body: JSON.stringify({ invoice_id: invoiceId })
      });

      if (!response.ok) {
        throw new Error('Failed to process payment');
      }

      const data: PaymentResponse = await response.json();
      
      toast({
        title: "Payment Processed",
        description: (
          <div className="mt-2 space-y-2">
            <p className="font-medium text-green-600">
              Successfully processed payment for Invoice #{data.payment_details.invoice_number}
            </p>
            <div className="text-sm text-gray-600 space-y-1">
              <p>Amount: {formatCurrency(data.payment_details.paid_amount)}</p>
              <p>Recipient: {data.payment_details.recipient}</p>
              <p>Payment ID: {data.invoice.payment_processing.payment_details.payment_id}</p>
              <p>Method: {data.invoice.payment_processing.payment_details.payment_method}</p>
              {data.payment_details.description && (
                <p className="text-xs text-gray-500">
                  Description: {data.payment_details.description}
                </p>
              )}
              <div className="mt-2 text-xs text-gray-500">
                <p>Bank: {data.payment_details.bank_details.bank_name}</p>
                <p>Account Holder: {data.payment_details.bank_details.account_holder_name}</p>
                <p>Type: {data.payment_details.bank_details.type}</p>
              </div>
              <p className="mt-2 text-xs text-gray-400">File: {data.file.name}</p>
            </div>
          </div>
        ),
        duration: 7000, // Show for 7 seconds due to more content
      });

      if (onPaymentComplete) {
        onPaymentComplete();
      }
    } catch (error) {
      console.error('Payment processing failed:', error);
      toast({
        variant: "destructive",
        title: "Payment Failed",
        description: "Failed to process the invoice payment. Please try again.",
        duration: 5000,
      });
    } finally {
      setProcessingPayments(prev => {
        const next = new Set(prev);
        next.delete(invoiceId);
        return next;
      });
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl font-semibold">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {invoices.map((invoice) => (
            <div
              key={invoice.id}
              className="border rounded-lg p-4 space-y-2 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <div className="font-medium">
                    Invoice #{invoice.data.invoice_number}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {invoice.data.recipient}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge
                    variant={invoice.status === "paid" ? "success" : "secondary"}
                  >
                    {invoice.status}
                  </Badge>
                  {invoice.status === "pending" && (
                    <Button
                      size="sm"
                      onClick={() => handlePayInvoice(invoice.id)}
                      disabled={processingPayments.has(invoice.id)}
                    >
                      {processingPayments.has(invoice.id) ? "Processing..." : "Pay Now"}
                    </Button>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="text-muted-foreground">Amount</div>
                  <div className="font-medium">
                    {formatCurrency(invoice.data.amount, invoice.data.currency)}
                  </div>
                </div>
                <div>
                  <div className="text-muted-foreground">Due Date</div>
                  <div className="font-medium">
                    {new Date(invoice.data.due_date).toLocaleDateString()}
                  </div>
                </div>
              </div>
            </div>
          ))}
          {invoices.length === 0 && (
            <div className="text-center text-muted-foreground py-8">
              No invoices found
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
} 