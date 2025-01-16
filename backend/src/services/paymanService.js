import { Paymanai } from "paymanai";
import dotenv from 'dotenv';

dotenv.config();

class PaymanService {
    constructor() {
        const config = {
            xPaymanAPISecret: process.env.PAYMAN_API_SECRET,
            baseURL: process.env.PAYMAN_BASE_URL
        };
        
        this.client = new Paymanai(config);
    }

    async processPayment(paymentData) {
        const timestamp = new Date().getTime();
        const payment = await this.client.payments.sendPayment({
            amountDecimal: paymentData.amount,
            customerEmail: paymentData.email || `payment+${timestamp}@example.com`,
            customerName: paymentData.recipientName,
            memo: paymentData.description,
            paymentDestination: {
                type: "US_ACH",
                accountHolderName: paymentData.recipientName,
                accountNumber: paymentData.accountNumber,
                accountType: "checking",
                routingNumber: paymentData.routingNumber,
                name: paymentData.recipientName,
                contactDetails: {
                    contactType: "business",
                    email: paymentData.email || `business+${timestamp}@example.com`,
                    phoneNumber: paymentData.phoneNumber || "+1234567890",
                    address: paymentData.address || "123 Business St, City, State 12345"
                }
            }
        });
        
        return typeof payment === 'string' ? JSON.parse(payment) : payment;
    }

    async getPaymentStatus(paymentId) {
        const payment = await this.client.payments.getPayment(paymentId);
        return payment.status;
    }

    async searchPayees(query) {
        const destinations = await this.client.payments.searchDestinations({
            name: query
        });
        return destinations;
    }

    async getBalance() {
        // Mock balance for testing since there's no direct balance API
        return {
            amount: 10000.00,
            currency: 'USD'
        };
    }
}

export default new PaymanService(); 