import { NextResponse } from 'next/server';
import { OpenAIToolSet } from 'composio-core';

if (!process.env.COMPOSIO_CLIENT_SECRET) {
  throw new Error('COMPOSIO_CLIENT_SECRET is not set in environment variables');
}

const toolset = new OpenAIToolSet({ 
  apiKey: process.env.COMPOSIO_CLIENT_SECRET
});

interface GmailProfileData {
  emailAddress: string;
  messagesTotal: number;
  threadsTotal: number;
  historyId: string;
}

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const accountId = searchParams.get('accountId');

    if (!accountId) {
      return NextResponse.json({ connected: false });
    }

    // Get the account details using the ConnectedAccounts class
    const accountDetails = await toolset.connectedAccounts.get({
      connectedAccountId: accountId
    });

    if (!accountDetails) {
      return NextResponse.json({ connected: false });
    }

    // Get Gmail profile using the GMAIL_GET_PROFILE action
    const profileResponse = await toolset.executeAction({
      action: 'GMAIL_GET_PROFILE',
      params: {
        user_id: 'me'
      },
      connectedAccountId: accountId
    });

    console.log("Profile Response:", profileResponse);
    
    if (!profileResponse.successful) {
      throw new Error(profileResponse.error || 'Failed to fetch Gmail profile');
    }

    const gmailData = (profileResponse.data as { response_data: GmailProfileData }).response_data;

    // Return the profile information
    return NextResponse.json({
      connected: true,
      profile: {
        emailAddress: gmailData.emailAddress,
        displayName: gmailData.emailAddress.split('@')[0] || 'Gmail Account',
        status: accountDetails.status,
        profileData: {
          emailAddress: gmailData.emailAddress,
          messagesTotal: gmailData.messagesTotal,
          threadsTotal: gmailData.threadsTotal,
          historyId: gmailData.historyId
        }
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