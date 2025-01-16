import { NextResponse } from 'next/server';
import { OpenAIToolSet } from 'composio-core';

if (!process.env.NEXT_PUBLIC_COMPOSIO_API_KEY) {
  throw new Error('NEXT_PUBLIC_COMPOSIO_API_KEY is not set in environment variables');
}

const toolset = new OpenAIToolSet({ 
  apiKey: process.env.NEXT_PUBLIC_COMPOSIO_API_KEY
});

export async function GET() {
  try {
    // Get the connected accounts
    const response = await toolset.connectedAccounts.list({
      integrationId: '73876b33-344e-44fc-81f4-628298823368'
    });

    // Check if we have any connected accounts
    const accounts = Array.isArray(response) ? response : [response];
    const connectedAccount = accounts.find(account => account.id);
    
    if (!connectedAccount) {
      return NextResponse.json({ connected: false });
    }

    // Get the Gmail profile using the connected account
    const accountDetails = await toolset.connectedAccounts.get({
      connectedAccountId: connectedAccount.id
    });

    return NextResponse.json({
      connected: true,
      profile: {
        emailAddress: accountDetails.id,
        displayName: 'Gmail Account',
        status: accountDetails.status
      }
    });
  } catch (error) {
    console.error('Gmail profile error:', error);
    return NextResponse.json(
      { message: error instanceof Error ? error.message : 'Failed to fetch Gmail profile' },
      { status: 500 }
    );
  }
} 