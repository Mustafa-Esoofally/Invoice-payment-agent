'use client';

import { useEffect } from 'react';

export default function AuthCallback() {
  useEffect(() => {
    const logAndSendMessage = () => {
      console.log('[AuthCallback] Component mounted', {
        timestamp: new Date().toISOString(),
        searchParams: window.location.search,
        hasOpener: !!window.opener,
        href: window.location.href,
        origin: window.location.origin
      });

      const searchParams = new URLSearchParams(window.location.search);
      const status = searchParams.get('status');
      const connectedAccountId = searchParams.get('connectedAccountId');
      const appName = searchParams.get('appName');
      const error = searchParams.get('error');

      console.log('[AuthCallback] Parsed search params:', {
        status,
        hasConnectedAccountId: !!connectedAccountId,
        connectedAccountId: connectedAccountId?.substring(0, 8) + '...',  // Log part of ID for debugging
        appName,
        hasError: !!error,
        error,
        timestamp: new Date().toISOString()
      });

      if (status === 'success' && connectedAccountId) {
        // Store in localStorage
        console.log('[AuthCallback] Storing connected account ID in localStorage');
        localStorage.setItem('gmailConnectedAccountId', connectedAccountId);
      }

      if (!window.opener) {
        console.error('[AuthCallback] No opener window found!');
        return;
      }

      try {
        if (status === 'success' && connectedAccountId) {
          console.log('[AuthCallback] Attempting to send success message');
          const message = { 
            type: 'GMAIL_AUTH_SUCCESS', 
            connectedAccountId,
            appName 
          };
          window.opener.postMessage(message, '*');
          console.log('[AuthCallback] Success message sent');
        } else if (error) {
          console.log('[AuthCallback] Attempting to send error message');
          window.opener.postMessage({ type: 'GMAIL_AUTH_ERROR', error }, '*');
          console.log('[AuthCallback] Error message sent');
        } else {
          console.log('[AuthCallback] Invalid status or missing connectedAccountId');
          window.opener.postMessage({ 
            type: 'GMAIL_AUTH_ERROR', 
            error: 'Invalid response from authentication server' 
          }, '*');
        }
      } catch (err) {
        console.error('[AuthCallback] Error sending message:', err);
      }
    };

    // Execute immediately
    logAndSendMessage();

    // Also try again after a short delay in case opener wasn't ready
    const retryTimeout = setTimeout(logAndSendMessage, 500);

    // Close the window after a delay
    const closeTimeout = setTimeout(() => {
      console.log('[AuthCallback] Closing window');
      window.close();
    }, 2000);  // Back to 2 seconds since we don't need 10s anymore

    return () => {
      console.log('[AuthCallback] Cleanup - clearing timeouts');
      clearTimeout(closeTimeout);
      clearTimeout(retryTimeout);
    };
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-xl font-semibold text-gray-900 mb-4">
          Gmail Authentication Complete
        </h1>
        <p className="text-gray-600">
          This window will close automatically...
        </p>
        <p className="text-sm text-gray-500 mt-2">
          If it doesn't close, you can close it manually.
        </p>
      </div>
    </div>
  );
} 