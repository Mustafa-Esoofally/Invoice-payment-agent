import { NextResponse } from 'next/server';
import { OpenAIToolSet } from 'composio-core';

if (!process.env.NEXT_PUBLIC_COMPOSIO_API_KEY) {
  throw new Error('NEXT_PUBLIC_COMPOSIO_API_KEY is not set in environment variables');
}

const toolset = new OpenAIToolSet({ 
  apiKey: process.env.NEXT_PUBLIC_COMPOSIO_API_KEY
});

export async function POST() {
  try {
    // Initialize Gmail connection
    const connectedAccount = await toolset.connectedAccounts.initiate({
      integrationId: '73876b33-344e-44fc-81f4-628298823368',
      entityId: 'default'
    });

    if (!connectedAccount.redirectUrl) {
      throw new Error('No redirect URL received');
    }

    return NextResponse.json({
      redirectUrl: connectedAccount.redirectUrl,
      accountId: connectedAccount.connectedAccountId
    });
  } catch (error) {
    console.error('Gmail auth error:', error);
    return NextResponse.json(
      { message: error instanceof Error ? error.message : 'Failed to initialize Gmail authentication' },
      { status: 500 }
    );
  }
} 