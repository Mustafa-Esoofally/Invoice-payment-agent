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
  const [isConnecting, setIsConnecting] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'success' | 'error' | null>(() => {
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
            fetchPaymentHistory();
          } else {
            localStorage.removeItem("gmailConnectedAccountId");
            setConnectionStatus(null);
            setProfile(null);
          }
        })
        .catch(error => {
          console.error('Failed to fetch profile:', error);
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
        fetch(`/api/auth/gmail/profile?accountId=${accountId}`)
          .then(res => res.json())
          .then(data => {
            if (data.connected && data.profile) {
              setProfile(data.profile);
              // Fetch payment history after profile is loaded
              fetchPaymentHistory();
            }
          });
      } else if (type === 'GMAIL_ERROR') {
        setIsConnecting(false);
        setConnectionStatus('error');
        setStatusMessage(error || 'Failed to connect Gmail account');
        localStorage.removeItem("gmailConnectedAccountId");
        setProfile(null);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [fetchPaymentHistory]);

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

  const successCount = paymentHistory.filter(payment => payment.payment.success).length;
  const failedCount = paymentHistory.filter(payment => !payment.payment.success).length;

  return (
    <div className="min-h-screen bg-gray-50/50">
      <div className="container py-8 px-4">
        {profile ? (
          <div className="w-full max-w-5xl mx-auto space-y-6">
            <div className="text-center space-y-2">
              <h1 className="text-3xl font-bold tracking-tight">Welcome to Invoice Payment Agent</h1>
              <p className="text-lg text-gray-600">Process your invoice emails automatically</p>
            </div>

            {connectionStatus === 'error' && (
              <Alert variant="destructive" className="border-red-200">
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{statusMessage}</AlertDescription>
              </Alert>
            )}

            <ProfileDetails profile={profile} />
            
            <ProcessInvoices 
              isProcessing={isProcessing}
              onProcess={handleProcessInvoices}
            />

            {paymentHistory.length > 0 && (
              <PaymentHistory 
                payments={paymentHistory}
                successCount={successCount}
                failedCount={failedCount}
              />
            )}
          </div>
        ) : (
          <div className="flex min-h-[80vh] items-center justify-center">
            <Card className="w-full max-w-md border-0 shadow-lg">
              <CardHeader className="text-center space-y-3">
                <CardTitle className="text-3xl font-bold tracking-tight">Welcome to Invoice Payment Agent</CardTitle>
                <CardDescription className="text-lg">
                  Connect your email to start managing your invoices automatically
                </CardDescription>
              </CardHeader>
              <CardContent>
                {connectionStatus === 'error' && (
                  <Alert variant="destructive" className="mb-6 border-red-200">
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{statusMessage}</AlertDescription>
                  </Alert>
                )}
                
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
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
