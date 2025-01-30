import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

interface Payment {
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

interface PaymentHistoryProps {
  payments: Payment[];
  successCount: number;
  failedCount: number;
}

export function PaymentHistory({ payments, successCount, failedCount }: PaymentHistoryProps) {
  const successfulPayments = payments.filter(payment => payment.payment.success);
  const failedPayments = payments.filter(payment => !payment.payment.success);

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium">Payment History</h3>
          <div className="text-sm space-x-3">
            <span className="text-muted-foreground">{payments.length} Total</span>
            <span className="text-emerald-600">{successCount} Success</span>
            <span className="text-red-600">{failedCount} Failed</span>
          </div>
        </div>

        <Tabs defaultValue="all">
          <TabsList className="mb-4">
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="successful">Successful</TabsTrigger>
            <TabsTrigger value="failed">Failed</TabsTrigger>
          </TabsList>

          <TabsContent value="all" className="mt-0">
            <PaymentTable payments={payments} />
          </TabsContent>
          <TabsContent value="successful" className="mt-0">
            <PaymentTable payments={successfulPayments} />
          </TabsContent>
          <TabsContent value="failed" className="mt-0">
            <PaymentTable payments={failedPayments} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

function PaymentTable({ payments }: { payments: Payment[] }) {
  return (
    <div className="border rounded-lg">
      <div className="grid grid-cols-5 gap-2 p-3 bg-gray-50 text-sm text-muted-foreground">
        <div>Date</div>
        <div>Invoice</div>
        <div>Recipient</div>
        <div>Amount</div>
        <div>Status</div>
      </div>
      <div>
        {payments.map((payment, index) => (
          <div key={index} className="grid grid-cols-5 gap-2 p-3 text-sm border-t">
            <div>{new Date(payment.timestamp).toLocaleDateString()}</div>
            <div>{payment.invoice.invoice_number}</div>
            <div>{payment.invoice.recipient}</div>
            <div>${payment.invoice.paid_amount.toLocaleString()}</div>
            <div>
              {payment.payment.success ? (
                <span className="text-xs text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
                  Success
                </span>
              ) : (
                <span className="text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded">
                  {payment.payment.error || 'Failed'}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
} 