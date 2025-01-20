'use client';

import { useEffect, useState, useRef } from 'react';

interface ProfileData {
  emailAddress: string;
  displayName: string;
  status: string;
}

interface GmailProfileProps {
  refreshTrigger?: number;
}

export default function GmailProfile({ refreshTrigger = 0 }: GmailProfileProps) {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pollCountRef = useRef(0);
  const pollIntervalRef = useRef<NodeJS.Timeout>();

  const fetchProfile = async () => {
    try {
      console.log('[GmailProfile] Fetching profile...', { 
        pollCount: pollCountRef.current,
        timestamp: new Date().toISOString()
      });
      setLoading(true);
      setError(null);
      
      // Fetch profile through our API
      console.log('[GmailProfile] Making API request to /api/gmail/profile');
      const response = await fetch('/api/gmail/profile');
      const data = await response.json();
      console.log('[GmailProfile] Profile API response:', {
        status: response.status,
        ok: response.ok,
        data,
        timestamp: new Date().toISOString()
      });
      
      if (!response.ok) {
        throw new Error(data.message || 'Failed to fetch Gmail profile');
      }

      if (!data.connected) {
        console.log('[GmailProfile] No connection found yet', {
          pollCount: pollCountRef.current,
          willContinuePolling: pollCountRef.current < 10
        });
        if (pollCountRef.current < 10) {
          // Keep polling if we haven't found the connection yet
          return;
        }
        console.log('[GmailProfile] Max poll attempts reached, stopping');
        setProfile(null);
        return;
      }

      console.log('[GmailProfile] Connection found, setting profile', {
        profile: data.profile,
        timestamp: new Date().toISOString()
      });

      // Clear polling if we got the profile
      if (pollIntervalRef.current) {
        console.log('[GmailProfile] Clearing poll interval');
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = undefined;
      }
      setProfile(data.profile);
    } catch (err) {
      console.error("[GmailProfile] Error fetching Gmail profile:", err);
      setError("Failed to fetch Gmail profile");
    } finally {
      setLoading(false);
      pollCountRef.current += 1;
      console.log('[GmailProfile] Fetch attempt complete', {
        newPollCount: pollCountRef.current,
        hasError: !!error,
        timestamp: new Date().toISOString()
      });
    }
  };

  // Start polling when refreshTrigger changes
  useEffect(() => {
    console.log('[GmailProfile] Refresh trigger changed:', {
      newValue: refreshTrigger,
      timestamp: new Date().toISOString()
    });
    
    // Reset poll count
    pollCountRef.current = 0;
    console.log('[GmailProfile] Reset poll count to 0');

    // Clear any existing polling
    if (pollIntervalRef.current) {
      console.log('[GmailProfile] Clearing existing poll interval');
      clearInterval(pollIntervalRef.current);
    }

    console.log('[GmailProfile] Setting up initial fetch with 1s delay');
    // Initial fetch after a short delay
    const initialFetchTimeout = setTimeout(() => {
      console.log('[GmailProfile] Initial delay complete, starting first fetch');
      fetchProfile();
      
      console.log('[GmailProfile] Setting up polling interval (2s)');
      // Start polling every 2 seconds
      pollIntervalRef.current = setInterval(() => {
        if (pollCountRef.current < 10) {
          console.log('[GmailProfile] Poll interval triggered', {
            pollCount: pollCountRef.current,
            timestamp: new Date().toISOString()
          });
          fetchProfile();
        } else {
          console.log('[GmailProfile] Max polls reached, cleaning up interval');
          // Stop polling after 10 attempts
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = undefined;
          }
        }
      }, 2000);
    }, 1000);

    // Cleanup
    return () => {
      console.log('[GmailProfile] Cleanup running', {
        hadInterval: !!pollIntervalRef.current,
        timestamp: new Date().toISOString()
      });
      clearTimeout(initialFetchTimeout);
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = undefined;
      }
    };
  }, [refreshTrigger]);

  if (loading && !profile) {
    return <div className="flex items-center justify-center p-4">Loading profile...</div>;
  }

  if (error) {
    return <div className="text-red-500 p-4">{error}</div>;
  }

  if (!profile) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6 max-w-sm mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Connected Account</h2>
        <span className="px-2 py-1 text-sm rounded-full bg-green-100 text-green-800">
          {profile.status}
        </span>
      </div>
      <div className="space-y-2">
        <p><span className="font-medium">Account:</span> {profile.displayName}</p>
        <p><span className="font-medium">ID:</span> {profile.emailAddress}</p>
      </div>
    </div>
  );
} 