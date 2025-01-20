import { NextResponse } from "next/server";
import { OpenAIToolSet } from 'composio-core';

const GMAIL_INTEGRATION_ID = '73876b33-344e-44fc-81f4-628298823368';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const code = searchParams.get('code');
    const state = searchParams.get('state');

    if (!code || !state) {
      throw new Error('Missing required OAuth parameters');
    }

    if (!process.env.COMPOSIO_CLIENT_SECRET) {
      throw new Error('COMPOSIO_CLIENT_SECRET is not set');
    }

    const toolset = new OpenAIToolSet({ 
      apiKey: process.env.COMPOSIO_CLIENT_SECRET,
    });

    // Exchange the OAuth code for a connected account
    const connectedAccount = await toolset.connectedAccounts.exchange({
      code,
      state
    });

    // Create HTML that will send a message to the opener window and close itself
    const html = `
      <!DOCTYPE html>
      <html>
        <body>
          <script>
            if (window.opener) {
              window.opener.postMessage({ 
                type: 'GMAIL_CONNECTED',
                accountId: '${connectedAccount.id}',
                message: 'Gmail account connected successfully'
              }, '*');
              window.close();
            }
          </script>
        </body>
      </html>
    `;

    return new NextResponse(html, {
      headers: { 'Content-Type': 'text/html' },
    });

  } catch (error) {
    console.error("Callback error:", error);
    const errorHtml = `
      <!DOCTYPE html>
      <html>
        <body>
          <script>
            if (window.opener) {
              window.opener.postMessage({ 
                type: 'GMAIL_ERROR',
                error: '${error instanceof Error ? error.message : 'Failed to connect Gmail account'}'
              }, '*');
              window.close();
            }
          </script>
        </body>
      </html>
    `;

    return new NextResponse(errorHtml, {
      headers: { 'Content-Type': 'text/html' },
    });
  }
} 