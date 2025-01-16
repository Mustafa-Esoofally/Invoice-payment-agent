import { PaymentDetails, PaymentStatus, PaymentDestination, BalanceInfo } from '../types/payment.js';
import { paymanClient } from './paymanClient.js';

export class PaymanService {
  async processPayment(paymentData: PaymentDetails): Promise<PaymentStatus> {
    try {
      // The API expects amount in dollars, so use it directly
      const amountDecimal = paymentData.amount;

      // Search for payment destination details
      const destinations = await paymanClient.payments.searchDestinations({
        name: paymentData.recipientName || ''
      });

      const destination = destinations && destinations.length > 0 ? destinations[0] : null;

      // Base payment request - don't include customer ID for agent payments
      const baseRequest = {
        amountDecimal,
        customerEmail: paymentData.email || 'unknown@example.com',
        customerName: paymentData.recipientName || paymentData.description || 'Unknown',
        memo: paymentData.memo || paymentData.description,
      };

      // Add payment destination - use the found destination ID if available
      const paymentRequest = {
        ...baseRequest,
        paymentDestinationId: destination?.id || paymentData.payeeId
      };

      console.log('Sending payment request:', JSON.stringify(paymentRequest, null, 2));

      // Use the Payman API to send payment
      const response = await paymanClient.payments.sendPayment(paymentRequest);

      // Log the response for debugging
      console.log('Payment API Response:', JSON.stringify(response, null, 2));

      // Generate payment status from response
      return {
        id: typeof response === 'object' && response && 'id' in response 
          ? String(response.id)
          : `pmt_${Date.now()}`,
        status: 'completed',
        amount: paymentData.amount,
        currency: paymentData.currency || 'USD',
        timestamp: new Date().toISOString()
      };
    } catch (error: any) {
      console.error('Payment processing error:', error);
      console.error('Error details:', {
        message: error.message,
        status: error.status,
        errorCode: error.error?.errorCode,
        errorMessage: error.error?.errorMessage,
        details: error.error?.details || error.details
      });
      throw new Error(`Payment failed: ${error.error?.errorMessage || error.message}`);
    }
  }

  async getPaymentStatus(paymentId: string): Promise<PaymentStatus> {
    // Since the API doesn't support status checking, return completed status
    return {
      id: paymentId,
      status: 'completed',
      amount: 0, // We don't store this information
      currency: 'USD',
      timestamp: new Date().toISOString()
    };
  }

  async searchPayees(query: string): Promise<PaymentDestination[]> {
    try {
      const response = await paymanClient.payments.searchDestinations({
        name: query
      });

      // Parse the response if it's a string
      const destinations = typeof response === 'string' ? JSON.parse(response) : response;

      if (!Array.isArray(destinations)) {
        console.warn('Unexpected response format from searchDestinations:', destinations);
        return [];
      }

      return destinations.map(dest => ({
        id: dest.id,
        name: dest.name || 'Unknown',
        email: dest.email || '',
        routingNumber: dest.destinationDetails?.['ach-routing-number'] || '',
        accountType: dest.destinationDetails?.['ach-type'] || 'business'
      }));
    } catch (error) {
      console.error('Search error:', error);
      return [];
    }
  }

  async getBalance(): Promise<BalanceInfo> {
    try {
      const response = await paymanClient.balances.getSpendableBalance('USD');
      console.log(response)  
      // The API returns a number directly, no need to parse
      return {
        available: Number(response) || 0,
        currency: 'USD'
      };
    } catch (error) {
      console.error('Balance check error:', error);
      // Return zero balance in case of error
      return {
        available: 0,
        currency: 'USD'
      };
    }
  }
} 