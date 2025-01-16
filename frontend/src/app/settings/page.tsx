'use client';

import { Suspense, useState, useCallback } from 'react';
import GmailAuth from '@/components/GmailAuth';
import GmailProfile from '@/components/GmailProfile';

export default function SettingsPage() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleAuthSuccess = useCallback((connectedAccountId: string) => {
    console.log('[Settings] Auth success callback with connectedAccountId:', {
      id: connectedAccountId.substring(0, 8) + '...',  // Log part of ID for debugging
      timestamp: new Date().toISOString()
    });

    // Store the ID in localStorage (as a backup, though it's also stored in the callback page)
    localStorage.setItem('gmailConnectedAccountId', connectedAccountId);
    
    console.log('[Settings] Triggering profile refresh...');
    // Wait a bit before triggering the refresh
    setTimeout(() => {
      setRefreshTrigger(prev => {
        console.log('[Settings] Incrementing refresh trigger:', prev + 1);
        return prev + 1;
      });
    }, 2000); // Wait 2 seconds before starting to poll for profile
  }, []);

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Settings</h1>
      
      <div className="grid gap-8">
        <section>
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Email Integration</h2>
          <div className="bg-gray-50 rounded-lg p-6">
            <Suspense fallback={<div>Loading...</div>}>
              <div className="space-y-6" id="gmail-section">
                <GmailProfile refreshTrigger={refreshTrigger} />
                <GmailAuth onAuthSuccess={handleAuthSuccess} />
              </div>
            </Suspense>
          </div>
        </section>
        
        <section>
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Invoice Processing</h2>
          <div className="bg-gray-50 rounded-lg p-6">
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-gray-900">Auto-Process Invoices</h3>
                  <p className="text-sm text-gray-600">
                    Automatically process invoices when they arrive in your inbox
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>
              
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-gray-900">Amount Threshold</h3>
                  <p className="text-sm text-gray-600">
                    Skip invoices above this amount
                  </p>
                </div>
                <input 
                  type="number" 
                  defaultValue="1000"
                  className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
} 