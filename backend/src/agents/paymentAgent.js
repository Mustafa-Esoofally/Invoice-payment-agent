import { ChatOpenAI } from '@langchain/openai';
import { initializeAgentExecutorWithOptions } from 'langchain/agents';
import { Tool } from '@langchain/core/tools';
import paymanService from '../services/paymanService.js';

class ProcessPaymentTool extends Tool {
    name = 'process_payment';
    description = 'Process a payment using Payman AI. Input should be a JSON string containing payment details (amount, recipientName, accountNumber, routingNumber, description)';

    async _call(inputStr) {
        const paymentData = JSON.parse(inputStr);
        if (paymentData.bankDetails?.routingNumber) {
            paymentData.routingNumber = paymentData.bankDetails.routingNumber;
            delete paymentData.bankDetails;
        }
        
        const payment = await paymanService.processPayment(paymentData);
        return `Successfully processed payment. Reference: ${payment.reference}`;
    }
}

class PaymentStatusTool extends Tool {
    name = 'check_payment_status';
    description = 'Check the status of a payment using its Payman payment reference';

    async _call(reference) {
        const status = await paymanService.getPaymentStatus(reference);
        return `Payment status for reference ${reference}: ${status}`;
    }
}

class SearchPayeesTool extends Tool {
    name = 'search_payees';
    description = 'Search for payees in the Payman system';

    async _call(query) {
        const payees = await paymanService.searchPayees(query);
        return JSON.stringify(payees, null, 2);
    }
}

class CheckBalanceTool extends Tool {
    name = 'check_balance';
    description = 'Check the current balance of the Payman account';

    async _call() {
        const balance = await paymanService.getBalance();
        return `Current balance: ${balance.amount} ${balance.currency}`;
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

    async invoke(input) {
        const result = await this.executor.invoke({ input });
        return result.output;
    }

    async processPayment(paymentDetails) {
        return this.invoke(`Process a payment with the following details: ${JSON.stringify(paymentDetails)}`);
    }

    async checkPaymentStatus(paymentId) {
        return this.invoke(`Check the status of payment with ID ${paymentId}`);
    }

    async searchPayees(query) {
        return this.invoke(`Search for payees matching: ${query}`);
    }

    async getBalance() {
        return this.invoke('Check the current balance of the Payman account');
    }
} 