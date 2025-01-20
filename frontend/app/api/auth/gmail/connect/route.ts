import { NextResponse } from "next/server";
import { OpenAIToolSet } from 'composio-core';

// Gmail integration ID from Composio
const GMAIL_INTEGRATION_ID = '73876b33-344e-44fc-81f4-628298823368';

export async function GET(request: Request) {
  try {
    console.log("Connecting to Gmail...");
    
    // Get the callback URL from environment
    const redirectUri = `${process.env.NEXT_PUBLIC_APP_URL}/auth/callback`;
    console.log("Redirect URI:", redirectUri);

    if (!process.env.COMPOSIO_CLIENT_SECRET) {
      throw new Error('COMPOSIO_CLIENT_SECRET is not set in environment variables');
    }

    const toolset = new OpenAIToolSet({ 
      apiKey: process.env.COMPOSIO_CLIENT_SECRET,
    });

    // Initialize Gmail connection directly with the known integration ID
    const connectedAccount = await toolset.connectedAccounts.initiate({
      integrationId: GMAIL_INTEGRATION_ID,
      entityId: 'default',
      redirectUri
    });

    if (!connectedAccount.redirectUrl) {
      throw new Error('No redirect URL received');
    }

    console.log("Redirect URL:", connectedAccount.redirectUrl);
    return NextResponse.redirect(connectedAccount.redirectUrl);
  } catch (error) {
    console.error("Gmail auth error:", error);
    return NextResponse.json({ 
      error: "Failed to initiate Gmail authentication",
      details: error instanceof Error ? error.message : String(error)
    }, { status: 500 });
  }
} 