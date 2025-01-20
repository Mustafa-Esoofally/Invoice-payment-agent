"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Mail, CheckCircle2, XCircle, RefreshCcw } from "lucide-react";
import { useCallback, useEffect, useState, useMemo } from "react";
import { toast } from "@/components/ui/use-toast";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface EmailProfile {
  emailAddress: string;
  displayName: string;
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
  const [isConnecting, setIsConnecting] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'success' | 'error' | null>(() => {
    // Initialize connection status based on localStorage
    if (typeof window !== 'undefined') {
      return localStorage.getItem("gmailConnectedAccountId") ? 'success' : null;
    }
    return null;
  });
  const [statusMessage, setStatusMessage] = useState('');
  const [profile, setProfile] = useState<EmailProfile | null>(null);
  const [paymentHistory, setPaymentHistory] = useState<PaymentHistory[]>([]);

  // Fetch payment history
  const fetchPaymentHistory = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/payment-history');
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

  // Fetch email profile and payment history on mount if we have an account ID
  useEffect(() => {
    const accountId = localStorage.getItem("gmailConnectedAccountId");
    if (accountId) {
      setConnectionStatus('success');
      fetch(`/api/auth/gmail/profile?accountId=${accountId}`)
        .then(res => res.json())
        .then(data => {
          if (data.connected && data.profile) {
            setProfile(data.profile);
            // Fetch payment history after profile is loaded
            fetchPaymentHistory();
          } else {
            // If profile fetch fails, clear stored ID and reset state
            localStorage.removeItem("gmailConnectedAccountId");
            setConnectionStatus(null);
            setProfile(null);
          }
        })
        .catch(error => {
          console.error('Failed to fetch profile:', error);
          // On error, clear stored ID and reset state
          localStorage.removeItem("gmailConnectedAccountId");
          setConnectionStatus('error');
          setStatusMessage('Failed to fetch email profile. Please reconnect your account.');
          setProfile(null);
        });
    }
  }, [fetchPaymentHistory]);

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const { type, accountId, message, error } = event.data;

      if (type === 'GMAIL_CONNECTED') {
        setIsConnecting(false);
        localStorage.setItem("gmailConnectedAccountId", accountId);
        setConnectionStatus('success');
        setStatusMessage('Gmail account connected successfully');
        // Fetch profile after connection
        fetch(`/api/auth/gmail/profile?accountId=${accountId}`)
          .then(res => res.json())
          .then(data => {
            if (data.connected && data.profile) {
              setProfile(data.profile);
            }
          });
      } else if (type === 'GMAIL_ERROR') {
        setIsConnecting(false);
        setConnectionStatus('error');
        setStatusMessage(error || 'Failed to connect Gmail account');
        // Clear any existing connection
        localStorage.removeItem("gmailConnectedAccountId");
        setProfile(null);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const handleGmailConnect = useCallback(() => {
    setIsConnecting(true);
    setConnectionStatus(null);
    setStatusMessage('');
    localStorage.removeItem("gmailConnectedAccountId");
    setProfile(null);
    
    const width = 600;
    const height = 600;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;

    window.open(
      "/api/auth/gmail/connect",
      "Connect Gmail",
      `width=${width},height=${height},left=${left},top=${top},popup=1`
    );
  }, []);

  const handleProcessInvoices = useCallback(async () => {
    try {
      setIsProcessing(true);
      const accountId = localStorage.getItem("gmailConnectedAccountId");
      if (!accountId) {
        setConnectionStatus(null);
        throw new Error("No connected account found");
      }

      const response = await fetch('http://localhost:8000/process-invoices', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          composio_account_id: accountId,
          max_results: 10,
          debug: true
        })
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Failed to process invoices');

      toast({
        title: "Processing Complete",
        description: `Successfully processed ${data.total_processed || 0} invoices`,
      });

      // Refresh payment history after processing
      fetchPaymentHistory();
    } catch (error) {
      console.error('Failed to process invoices:', error);
      toast({
        variant: "destructive",
        title: "Processing Failed",
        description: error instanceof Error ? error.message : "Failed to process invoices",
      });
    } finally {
      setIsProcessing(false);
    }
  }, [fetchPaymentHistory]);

  // Memoized payment history filters
  const successfulPayments = useMemo(() => 
    paymentHistory.filter(payment => payment.payment.success),
    [paymentHistory]
  );

  const failedPayments = useMemo(() => 
    paymentHistory.filter(payment => !payment.payment.success),
    [paymentHistory]
  );

  // Payment history table component
  const PaymentTable = ({ payments }: { payments: PaymentHistory[] }) => (
    <div className="rounded-lg border bg-white shadow-sm">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/50 hover:bg-muted/50">
            <TableHead className="w-[180px] font-semibold">Date</TableHead>
            <TableHead className="w-[150px] font-semibold">Invoice Number</TableHead>
            <TableHead className="font-semibold">Recipient</TableHead>
            <TableHead className="w-[120px] font-semibold text-right">Amount</TableHead>
            <TableHead className="w-[120px] font-semibold">Status</TableHead>
            <TableHead className="font-semibold">Reference/Error</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {payments.map((payment, index) => (
            <TableRow key={index} className="hover:bg-muted/30">
              <TableCell className="whitespace-nowrap font-medium text-gray-600">
                {new Date(payment.timestamp).toLocaleString(undefined, {
                  year: 'numeric',
                  month: 'numeric',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </TableCell>
              <TableCell className="font-medium text-gray-900">{payment.invoice.invoice_number}</TableCell>
              <TableCell className="font-medium text-gray-900">{payment.invoice.recipient}</TableCell>
              <TableCell className="text-right font-semibold text-gray-900">
                ${payment.payment.amount.toLocaleString('en-US', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2
                })}
              </TableCell>
              <TableCell>
                {payment.payment.success ? (
                  <span className="inline-flex items-center px-2.5 py-1.5 rounded-full text-sm font-medium bg-green-50 text-green-700 border border-green-100">
                    <CheckCircle2 className="h-4 w-4 mr-1.5" />
                    Success
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2.5 py-1.5 rounded-full text-sm font-medium bg-red-50 text-red-700 border border-red-100">
                    <XCircle className="h-4 w-4 mr-1.5" />
                    Failed
                  </span>
                )}
              </TableCell>
              <TableCell className="max-w-md truncate text-gray-600">
                {payment.payment.success ? payment.payment.reference : payment.payment.error}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
        <TableCaption className="py-4 text-gray-500">
          {payments.length === 0 ? 'No payments found.' : 'A list of your recent invoice payments.'}
        </TableCaption>
      </Table>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50/50">
      <div className="container py-8 px-4">
        <Card className="w-full max-w-5xl mx-auto border-0 shadow-lg">
          <CardHeader className="text-center space-y-3 pb-8">
            <CardTitle className="text-3xl font-bold tracking-tight">Welcome to Invoice Payment Agent</CardTitle>
            <CardDescription className="text-lg text-gray-600">
              {profile ? 'Process your invoice emails automatically' : 'Connect your email to start managing your invoices automatically'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-8">
            {connectionStatus === 'error' && (
              <Alert variant="destructive" className="border-red-200">
                <XCircle className="h-4 w-4" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{statusMessage}</AlertDescription>
              </Alert>
            )}

            {profile ? (
              <div className="space-y-8">
                <Alert variant="default" className="bg-white border shadow-sm">
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                  <AlertTitle className="text-lg font-semibold mb-2">Connected Account</AlertTitle>
                  <AlertDescription>
                    <div className="grid grid-cols-2 gap-6">
                      <div className="space-y-1">
                        <span className="text-sm text-gray-500">Name</span>
                        <p className="font-medium text-gray-900">{profile.displayName}</p>
                      </div>
                      <div className="space-y-1">
                        <span className="text-sm text-gray-500">Email</span>
                        <p className="font-medium text-gray-900">{profile.emailAddress}</p>
                      </div>
                    </div>
                  </AlertDescription>
                </Alert>

                <Button 
                  size="lg" 
                  className="w-full bg-black hover:bg-gray-800 text-white shadow-sm transition-all duration-200 hover:shadow-md"
                  onClick={handleProcessInvoices}
                  disabled={isProcessing}
                >
                  {isProcessing ? (
                    <>
                      <RefreshCcw className="mr-2.5 h-5 w-5 animate-spin" />
                      Processing Invoices...
                    </>
                  ) : (
                    <>
                      <RefreshCcw className="mr-2.5 h-5 w-5" />
                      Process Invoices
                    </>
                  )}
                </Button>

                {paymentHistory.length > 0 && (
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xl font-semibold text-gray-900">Payment History</h3>
                      <div className="flex items-center gap-4 text-sm">
                        <div className="flex items-center gap-1.5">
                          <span className="h-2 w-2 rounded-full bg-gray-400"></span>
                          <span className="text-gray-600">Total: {paymentHistory.length}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="h-2 w-2 rounded-full bg-green-500"></span>
                          <span className="text-gray-600">Success: {successfulPayments.length}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="h-2 w-2 rounded-full bg-red-500"></span>
                          <span className="text-gray-600">Failed: {failedPayments.length}</span>
                        </div>
                      </div>
                    </div>
                    
                    <Tabs defaultValue="all" className="w-full">
                      <TabsList className="grid w-full grid-cols-3 gap-4 bg-muted/50 p-1">
                        <TabsTrigger 
                          value="all"
                          className="data-[state=active]:bg-white data-[state=active]:text-gray-900 data-[state=active]:shadow-sm"
                        >
                          All Payments
                        </TabsTrigger>
                        <TabsTrigger 
                          value="successful"
                          className="data-[state=active]:bg-white data-[state=active]:text-gray-900 data-[state=active]:shadow-sm"
                        >
                          Successful
                        </TabsTrigger>
                        <TabsTrigger 
                          value="failed"
                          className="data-[state=active]:bg-white data-[state=active]:text-gray-900 data-[state=active]:shadow-sm"
                        >
                          Failed
                        </TabsTrigger>
                      </TabsList>
                      <TabsContent value="all" className="mt-6">
                        <PaymentTable payments={paymentHistory} />
                      </TabsContent>
                      <TabsContent value="successful" className="mt-6">
                        <PaymentTable payments={successfulPayments} />
                      </TabsContent>
                      <TabsContent value="failed" className="mt-6">
                        <PaymentTable payments={failedPayments} />
                      </TabsContent>
                    </Tabs>
                  </div>
                )}
              </div>
            ) : (
              <Button 
                size="lg" 
                className="w-full bg-black hover:bg-gray-800 text-white shadow-sm transition-all duration-200 hover:shadow-md"
                onClick={handleGmailConnect}
                disabled={isConnecting}
              >
                {isConnecting ? (
                  <>
                    <Mail className="mr-2.5 h-5 w-5 animate-pulse" />
                    Connecting...
                  </>
                ) : (
                  <>
                    <Mail className="mr-2.5 h-5 w-5" />
                    Connect Gmail Account
                  </>
                )}
              </Button>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
