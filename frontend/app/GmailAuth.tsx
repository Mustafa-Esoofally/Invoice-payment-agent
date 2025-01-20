"use client";

import { useEffect, useCallback } from 'react';
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { Toaster } from "@/components/ui/toaster";

interface GmailAuthProps {
  onAuthSuccess?: (connectedAccountId: string) => void;
}

export default function GmailAuth({ onAuthSuccess }: GmailAuthProps) {
  const { toast } = useToast();

  const handleConnect = useCallback(async () => {
    try {
      const response = await fetch('/api/auth/gmail/connect');
      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      // Open the OAuth popup
      const width = 600;
      const height = 700;
      const left = window.screenX + (window.outerWidth - width) / 2;
      const top = window.screenY + (window.outerHeight - height) / 2;
      
      window.open(
        data.redirectUrl,
        'Gmail Login',
        `width=${width},height=${height},left=${left},top=${top}`
      );
    } catch (error) {
      console.error('Failed to initiate Gmail connection:', error);
      toast({
        variant: "destructive",
        title: "Connection Failed",
        description: error instanceof Error ? error.message : "Failed to connect Gmail account"
      });
    }
  }, [toast]);

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const { type, accountId, message, error } = event.data;

      if (type === 'GMAIL_CONNECTED') {
        toast({
          title: "Success",
          description: message || "Gmail account connected successfully"
        });
        onAuthSuccess?.(accountId);
      } else if (type === 'GMAIL_ERROR') {
        toast({
          variant: "destructive",
          title: "Connection Failed",
          description: error || "Failed to connect Gmail account"
        });
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [toast, onAuthSuccess]);

  return (
    <>
      <Button onClick={handleConnect}>
        Connect Gmail
      </Button>
      <Toaster />
    </>
  );
}