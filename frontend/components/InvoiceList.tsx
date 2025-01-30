import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Invoice } from "@/types/invoice";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";
import { useState } from "react";
import { toast } from "@/components/ui/use-toast";
import { createAuthHeader } from "@/lib/utils";

interface InvoiceListProps {
  invoices: Invoice[];
  title: string;
  onPaymentComplete?: () => void;
}

export function InvoiceList({ invoices, title, onPaymentComplete }: InvoiceListProps) {
  const [processingPayments, setProcessingPayments] = useState<Set<string>>(new Set());

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

      const data = await response.json();
      
      toast({
        title: "Payment Processed",
        description: "Invoice payment has been processed successfully",
      });

      if (onPaymentComplete) {
        onPaymentComplete();
      }
    } catch (error) {
      console.error('Payment processing failed:', error);
      toast({
        variant: "destructive",
        title: "Payment Failed",
        description: "Failed to process the invoice payment",
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