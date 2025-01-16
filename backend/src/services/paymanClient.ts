import { Paymanai } from 'paymanai';
import { config as dotenvConfig } from 'dotenv';

// Load environment variables
dotenvConfig();

// Verify required environment variables
const requiredEnvVars = [
  'PAYMAN_API_SECRET',
  'PAYMAN_BASE_URL',
  'OPENAI_API_KEY',
  'OPENAI_MODEL',
];

for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    throw new Error(`Missing required environment variable: ${envVar}`);
  }
}

// Create and export a single Payman client instance
export const paymanClient = new Paymanai({
  xPaymanAPISecret: process.env.PAYMAN_API_SECRET,
  baseURL: process.env.PAYMAN_BASE_URL
});

// Helper function to generate checkout URLs
export async function generateCheckoutUrl(amount: number, customerId: string, customerEmail: string, memo: string) {
  try {
    // Format amount to decimal with exactly 2 decimal places for USD
    const amountDecimal = Number(amount.toFixed(2));

    console.log('Initiating customer deposit with:', {
      amountDecimal,
      customerId,
      customerEmail,
      memo
    });

    const response = await paymanClient.payments.initiateCustomerDeposit({
      amountDecimal,
      customerId,
      customerEmail,
      memo
    });

    console.log('Response:', response);

    // The response might be a string, try to parse it
    const parsedResponse = typeof response === 'string' ? JSON.parse(response) : response;

    if (!parsedResponse || typeof parsedResponse !== 'object') {
      throw new Error('Invalid response format from API');
    }

    // The checkout URL might be in different formats depending on the API version
    const checkoutUrl = parsedResponse.checkoutUrl || parsedResponse.url || parsedResponse.paymentUrl;

    if (!checkoutUrl) {
      throw new Error('No checkout URL in API response');
    }

    console.log('Successfully generated checkout URL');
    return checkoutUrl;
  } catch (error: any) {
    // Log the full error for debugging
    console.error('Full API Error:', error);
    console.error('Payman API Error:', {
      message: error.message,
      status: error.status,
      errorCode: error.error?.errorCode,
      errorMessage: error.error?.errorMessage
    });
    throw error;
  }
}

// Helper function to send payments
export async function sendPayment(params: {
  amount: number;
  customerId?: string;
  customerEmail?: string;
  customerName?: string;
  memo: string;
  paymentDestinationId: string;
}) {
  // Convert amount to decimal format (e.g., 2500 -> 2500.00)
  const amountDecimal = Number(params.amount.toFixed(2));
  
  return paymanClient.payments.sendPayment({
    amountDecimal,
    customerId: params.customerId,
    customerEmail: params.customerEmail,
    customerName: params.customerName,
    memo: params.memo,
    paymentDestinationId: params.paymentDestinationId
  });
}

// Helper function to search payment destinations
export async function searchPaymentDestinations(params?: {
  name?: string;
  contactEmail?: string;
  type?: string;
}) {
  return paymanClient.payments.searchDestinations(params);
} 