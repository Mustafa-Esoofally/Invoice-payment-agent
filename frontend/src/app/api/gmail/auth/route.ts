import { NextResponse } from 'next/server';
import { OpenAIToolSet } from 'composio-core';

const COMPOSIO_API_KEY = process.env.NEXT_PUBLIC_COMPOSIO_API_KEY;
const GMAIL_INTEGRATION_ID = '73876b33-344e-44fc-81f4-628298823368';

export async function POST(request: Request) {
  try {
    if (!COMPOSIO_API_KEY) {
      throw new Error('COMPOSIO_API_KEY is not set');
    }

    const { redirectUri } = await request.json();

    const toolset = new OpenAIToolSet({ 
      apiKey: COMPOSIO_API_KEY
    });

    // Initialize Gmail connection
    const connectedAccount = await toolset.connectedAccounts.initiate({
      integrationId: GMAIL_INTEGRATION_ID,
      entityId: 'default',
      redirectUri
    });

    if (!connectedAccount.redirectUrl) {
      throw new Error('No redirect URL received');
    }

    return NextResponse.json({
      redirectUrl: connectedAccount.redirectUrl
    });
  } catch (error) {
    console.error('Gmail auth error:', error);
    return NextResponse.json(
      { message: error instanceof Error ? error.message : 'Failed to initialize Gmail authentication' },
      { status: 500 }
    );
  }
} 