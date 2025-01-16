"use client";

import { useEffect, useCallback, useRef } from 'react';

interface GmailAuthProps {
  onAuthSuccess?: (connectedAccountId: string) => void;
}

export default function GmailAuth({ onAuthSuccess }: GmailAuthProps) {
  const popupRef = useRef<Window | null>(null);

  const handleMessage = useCallback((event: MessageEvent) => {
    console.log('[GmailAuth] Received message:', {
      type: event.data?.type,
      origin: event.origin,
      sourceWindow: event.source === popupRef.current ? 'popup' : 'other',
      timestamp: new Date().toISOString(),
      data: event.data
    });

    // Accept messages from any origin since the popup might be on a different domain
    if (event.source !== popupRef.current) {
      console.log('[GmailAuth] Ignoring message from unknown source');
      return;
    }

    if (event.data?.type === 'GMAIL_AUTH_SUCCESS') {
      const { connectedAccountId, appName } = event.data;
      
      console.log('[GmailAuth] Auth success message received', {
        hasConnectedAccountId: !!connectedAccountId,
        connectedAccountId: connectedAccountId?.substring(0, 8) + '...',  // Log part of ID for debugging
        appName,
        timestamp: new Date().toISOString()
      });
      
      if (!connectedAccountId) {
        console.error('[GmailAuth] Success message missing connectedAccountId');
        return;
      }

      try {
        console.log('[GmailAuth] Calling onAuthSuccess callback with connectedAccountId');
        onAuthSuccess?.(connectedAccountId);
        console.log('[GmailAuth] Callback completed');
      } catch (err) {
        console.error('[GmailAuth] Error in auth success callback:', err);
      }
    } else if (event.data?.type === 'GMAIL_AUTH_ERROR') {
      console.error('[GmailAuth] Auth error message received:', {
        error: event.data.error,
        timestamp: new Date().toISOString()
      });
    } else {
      console.log('[GmailAuth] Ignoring unknown message type:', event.data?.type);
    }
  }, [onAuthSuccess]);

  useEffect(() => {
    console.log('[GmailAuth] Setting up message listener');
    window.addEventListener('message', handleMessage);
    return () => {
      console.log('[GmailAuth] Cleaning up message listener');
      window.removeEventListener('message', handleMessage);
    };
  }, [handleMessage]);

  const handleAuth = async () => {
    try {
      console.log('[GmailAuth] Starting auth process');
      const response = await fetch('/api/gmail/auth', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          redirectUri: `${window.location.origin}/auth/callback`,
        }),
      });

      console.log('[GmailAuth] Auth API response:', {
        status: response.status,
        ok: response.ok,
        timestamp: new Date().toISOString()
      });

      if (!response.ok) {
        const error = await response.json();
        console.error('[GmailAuth] Auth API error:', error);
        throw new Error(error.message || 'Failed to initialize Gmail authentication');
      }

      const data = await response.json();
      console.log('[GmailAuth] Received redirect URL:', {
        url: data.redirectUrl?.split('?')[0], // Log base URL without params
        timestamp: new Date().toISOString()
      });

      // Calculate popup dimensions and position
      const width = 600;
      const height = 700;
      const left = window.screenX + (window.outerWidth - width) / 2;
      const top = window.screenY + (window.outerHeight - height) / 2;

      console.log('[GmailAuth] Opening auth popup', {
        width,
        height,
        left,
        top,
        timestamp: new Date().toISOString()
      });

      // Store reference to popup window
      popupRef.current = window.open(
        data.redirectUrl,
        'Gmail Authentication',
        `width=${width},height=${height},left=${left},top=${top}`
      );

      if (!popupRef.current) {
        console.error('[GmailAuth] Failed to open popup window');
      }
    } catch (error) {
      console.error('[GmailAuth] Error during auth process:', error);
    }
  };

  return (
    <button
      onClick={handleAuth}
      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
    >
      Connect Gmail
    </button>
  );
}