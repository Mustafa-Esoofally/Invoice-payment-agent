"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Loader2 } from "lucide-react";

export default function CallbackPage() {
  const searchParams = useSearchParams();

  useEffect(() => {
    const logAndSendMessage = () => {
      const status = searchParams.get("status");
      const connectedAccountId = searchParams.get("connectedAccountId");
      const error = searchParams.get("error");

      console.log("Callback params:", { status, connectedAccountId, error });

      if (!window.opener) {
        console.error("No opener window found!");
        return;
      }

      try {
        if (status === "success" && connectedAccountId) {
          // Store in localStorage
          localStorage.setItem("gmailConnectedAccountId", connectedAccountId);
          
          // Send success message
          window.opener.postMessage({
            type: "GMAIL_CONNECTED",
            accountId: connectedAccountId,
            message: "Gmail account connected successfully"
          }, "*");
        } else if (error) {
          window.opener.postMessage({
            type: "GMAIL_ERROR",
            error: error
          }, "*");
        } else {
          window.opener.postMessage({
            type: "GMAIL_ERROR",
            error: "Invalid response from authentication server"
          }, "*");
        }
      } catch (err) {
        console.error("Error sending message:", err);
      }
    };

    // Execute immediately
    logAndSendMessage();

    // Also try again after a short delay in case opener wasn't ready
    const retryTimeout = setTimeout(logAndSendMessage, 500);

    // Close the window after a delay
    const closeTimeout = setTimeout(() => {
      console.log("Closing callback window");
      window.close();
    }, 2000);

    return () => {
      clearTimeout(retryTimeout);
      clearTimeout(closeTimeout);
    };
  }, [searchParams]);

  return (
    <div className="container flex items-center justify-center min-h-screen py-10">
      <Card className="w-full max-w-md">
        <CardContent className="flex flex-col items-center justify-center p-6 space-y-4">
          <Loader2 className="h-8 w-8 animate-spin" />
          <p className="text-center text-sm text-muted-foreground">
            Completing Gmail connection...
          </p>
        </CardContent>
      </Card>
    </div>
  );
} 