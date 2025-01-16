import { ChatOpenAI } from '@langchain/openai';
import { initializeAgentExecutorWithOptions } from 'langchain/agents';
import { Tool } from '@langchain/core/tools';
import paymanService from '../services/paymanService.js';

class ProcessPaymentTool extends Tool {
    name = 'process_payment';
    description = 'Process a payment using Payman AI. Input should be a JSON string containing payment details (amount, recipientName, accountNumber, routingNumber, description)';

    async _call(inputStr) {
        try {
            const paymentData = JSON.parse(inputStr);
            // Extract routingNumber from the input if it's nested
            if (paymentData.bankDetails && paymentData.bankDetails.routingNumber) {
                paymentData.routingNumber = paymentData.bankDetails.routingNumber;
                delete paymentData.bankDetails;
            }
            
            const payment = await paymanService.processPayment(paymentData);
            return `Successfully processed payment. Payment ID: ${payment.id}`;
        } catch (error) {
            console.error('Error processing payment:', error);
            throw error;
        }
    }
}

class PaymentStatusTool extends Tool {
    name = 'check_payment_status';
    description = 'Check the status of a payment using its Payman payment ID';

    async _call(paymentId) {
        try {
            const status = await paymanService.getPaymentStatus(paymentId);
            return `Payment status for ID ${paymentId}: ${status}`;
        } catch (error) {
            console.error('Error checking payment status:', error);
            throw error;
        }
    }
}

class SearchPayeesTool extends Tool {
    name = 'search_payees';
    description = 'Search for payees in the Payman system';

    async _call(query) {
        try {
            const payees = await paymanService.searchPayees(query);
            return JSON.stringify(payees, null, 2);
        } catch (error) {
            console.error('Error searching payees:', error);
            throw error;
        }
    }
}

class CheckBalanceTool extends Tool {
    name = 'check_balance';
    description = 'Check the current balance of the Payman account';

    async _call() {
        try {
            const balance = await paymanService.getBalance();
            return `Current balance: ${balance.amount} ${balance.currency}`;
        } catch (error) {
            console.error('Error checking balance:', error);
            throw error;
        }
    }
}

export class PaymentAgent {
    constructor() {
        this.llm = new ChatOpenAI({
            modelName: 'gpt-4',
            temperature: 0,
        });
        this.tools = [
            new ProcessPaymentTool(),
            new PaymentStatusTool(),
            new SearchPayeesTool(),
            new CheckBalanceTool(),
        ];
    }

    async initialize() {
        this.executor = await initializeAgentExecutorWithOptions(
            this.tools,
            this.llm,
            {
                agentType: 'openai-functions',
                verbose: true,
                maxIterations: 3,
            }
        );
        return this;
    }

    async processPayment(paymentDetails) {
        try {
            const result = await this.executor.invoke({
                input: `Process a payment with the following details: ${JSON.stringify(paymentDetails)}`,
            });
            return result.output;
        } catch (error) {
            console.error('Error in payment agent:', error);
            throw error;
        }
    }

    async checkPaymentStatus(paymentId) {
        try {
            const result = await this.executor.invoke({
                input: `Check the status of payment with ID ${paymentId}`,
            });
            return result.output;
        } catch (error) {
            console.error('Error checking payment status:', error);
            throw error;
        }
    }

    async searchPayees(query) {
        try {
            const result = await this.executor.invoke({
                input: `Search for payees matching: ${query}`,
            });
            return result.output;
        } catch (error) {
            console.error('Error searching payees:', error);
            throw error;
        }
    }

    async getBalance() {
        try {
            const result = await this.executor.invoke({
                input: 'Check the current balance of the Payman account',
            });
            return result.output;
        } catch (error) {
            console.error('Error getting balance:', error);
            throw error;
        }
    }
} 