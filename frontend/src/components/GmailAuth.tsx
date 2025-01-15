"use client";

import { Button } from "./ui/button";
import { useState, useEffect } from "react";

export default function GmailAuth() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authWindow, setAuthWindow] = useState<Window | null>(null);

  // Handle the popup window messages
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      // Verify the origin of the message
      if (event.origin !== window.location.origin) return;

      if (event.data?.type === 'GMAIL_AUTH_SUCCESS') {
        // Close the popup
        authWindow?.close();
        setAuthWindow(null);
        // Handle successful authentication
        console.log('Gmail authentication successful:', event.data);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [authWindow]);

  const handleAuth = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Initialize Gmail connection
      const response = await fetch('/api/auth/gmail/connect', {
        method: 'POST',
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || 'Failed to initialize Gmail authentication');
      }

      // Open authentication in a popup
      if (data.redirectUrl) {
        const width = 600;
        const height = 700;
        const left = window.screenX + (window.outerWidth - width) / 2;
        const top = window.screenY + (window.outerHeight - height) / 2;

        const popup = window.open(
          data.redirectUrl,
          'Gmail Authentication',
          `width=${width},height=${height},left=${left},top=${top},popup=1`
        );

        if (popup) {
          setAuthWindow(popup);
          
          // Check if popup was closed
          const checkClosed = setInterval(() => {
            if (popup.closed) {
              clearInterval(checkClosed);
              setAuthWindow(null);
              setLoading(false);
            }
          }, 1000);
        } else {
          throw new Error('Please enable popups for Gmail authentication');
        }
      } else {
        throw new Error('No redirect URL received');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to authenticate");
      console.error('Auth error:', err);
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <Button
        onClick={handleAuth}
        disabled={loading}
        className="w-full"
      >
        {loading ? "Connecting..." : "Connect Gmail"}
      </Button>
      {error && <p className="text-red-500 text-sm">{error}</p>}
    </div>
  );
}