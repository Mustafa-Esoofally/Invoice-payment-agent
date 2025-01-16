import Paymanai from "paymanai";
import dotenv from 'dotenv';

// Ensure dotenv is configured before any code runs
dotenv.config();

console.log('Environment check:');
console.log('PAYMAN_API_SECRET:', process.env.PAYMAN_API_SECRET ? 'Present' : 'Missing');
console.log('PAYMAN_BASE_URL:', process.env.PAYMAN_BASE_URL);

class PaymanService {
    constructor() {
        console.log('Initializing PaymanService...');
        try {
            const config = {
                xPaymanAPISecret: process.env.PAYMAN_API_SECRET,
                environment: "sandbox"
            };
            console.log('Payman config:', { ...config, xPaymanAPISecret: '[REDACTED]' });
            
            this.client = new Paymanai(config);
            console.log('Payman client initialized successfully');
        } catch (error) {
            console.error('Error initializing Payman client:', error);
            throw error;
        }
    }

    async processPayment(paymentData) {
        try {
            console.log('Processing payment with data:', {
                ...paymentData,
                accountNumber: '[REDACTED]',
                routingNumber: '[REDACTED]'
            });

            // First, search for existing payee
            const destinations = await this.client.payments.searchDestinations({
                name: paymentData.recipientName
            });

            let payment;
            if (destinations && destinations.length > 0) {
                // Use existing payee
                payment = await this.client.payments.sendPayment({
                    amountDecimal: paymentData.amount,
                    memo: paymentData.description,
                    paymentDestinationId: destinations[0].id
                });
            } else {
                // Create new payment destination inline
                const paymentDestination = {
                    type: "US_ACH",
                    accountHolderName: paymentData.recipientName,
                    accountNumber: paymentData.accountNumber,
                    accountType: "checking",
                    routingNumber: paymentData.routingNumber,
                    name: paymentData.recipientName,
                    contactDetails: {
                        contactType: "business",
                        email: paymentData.email || "contact@example.com",
                        phoneNumber: paymentData.phoneNumber || "+1234567890",
                        address: paymentData.address || "123 Business St, City, State 12345"
                    }
                };

                payment = await this.client.payments.sendPayment({
                    amountDecimal: paymentData.amount,
                    memo: paymentData.description,
                    paymentDestination: paymentDestination
                });
            }
            
            console.log('Payment processed successfully:', payment.id);
            return payment;
        } catch (error) {
            console.error('Error processing payment:', error);
            throw error;
        }
    }

    async getPaymentStatus(paymentId) {
        try {
            console.log('Checking payment status for ID:', paymentId);
            const payment = await this.client.payments.getPayment(paymentId);
            console.log('Payment status retrieved:', payment.status);
            return payment.status;
        } catch (error) {
            console.error('Error getting payment status:', error);
            throw error;
        }
    }

    async searchPayees(query) {
        try {
            console.log('Searching payees with query:', query);
            const destinations = await this.client.payments.searchDestinations({
                name: query
            });
            console.log('Found destinations:', destinations.length);
            return destinations;
        } catch (error) {
            console.error('Error searching payees:', error);
            throw error;
        }
    }

    async getBalance() {
        try {
            console.log('Fetching balance...');
            const balance = await this.client.payments.getBalance();
            console.log('Balance retrieved:', balance);
            return balance;
        } catch (error) {
            console.error('Error getting balance:', error);
            throw error;
        }
    }
}

export default new PaymanService(); 