import { NextResponse } from "next/server";
import { OpenAIToolSet } from 'composio-core';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const accountId = searchParams.get('accountId');
    
    if (!accountId) {
      return NextResponse.json({ connected: false });
    }

    if (!process.env.COMPOSIO_CLIENT_SECRET) {
      throw new Error('COMPOSIO_CLIENT_SECRET is not set');
    }

    const toolset = new OpenAIToolSet({ 
      apiKey: process.env.COMPOSIO_CLIENT_SECRET,
    });

    // Get the connected account details
    const accountDetails = await toolset.connectedAccounts.get({
      connectedAccountId: accountId
    });

    if (!accountDetails) {
      return NextResponse.json({ connected: false });
    }

    return NextResponse.json({
      connected: true,
      profile: {
        emailAddress: accountDetails.id,
        displayName: 'Gmail Account'
      }
    });

  } catch (error) {
    console.error("Gmail profile error:", error);
    return NextResponse.json(
      { 
        connected: false,
        error: error instanceof Error ? error.message : "Failed to fetch Gmail profile"
      },
      { status: 500 }
    );
  }
} 