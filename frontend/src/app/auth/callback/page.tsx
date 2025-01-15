'use client';

import { useEffect } from 'react';
import { useSearchParams } from 'next/navigation';

export default function AuthCallback() {
  const searchParams = useSearchParams();

  useEffect(() => {
    const code = searchParams.get('code');
    const error = searchParams.get('error');

    if (code) {
      // Send success message to parent window
      window.opener?.postMessage(
        {
          type: 'GMAIL_AUTH_SUCCESS',
          code,
        },
        window.location.origin
      );
    } else if (error) {
      // Send error message to parent window
      window.opener?.postMessage(
        {
          type: 'GMAIL_AUTH_ERROR',
          error,
        },
        window.location.origin
      );
    }

    // Close this window after sending the message
    if (window.opener) {
      window.close();
    }
  }, [searchParams]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-center text-gray-500">
        Completing authentication...
      </p>
    </div>
  );
} 