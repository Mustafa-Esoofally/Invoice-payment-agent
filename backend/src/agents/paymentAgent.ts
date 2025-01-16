import { ChatOpenAI } from '@langchain/openai';
import { DynamicTool } from '@langchain/core/tools';
import { PaymanService } from '../services/paymanService.js';
import { PaymentDetails, PaymentStatus, PaymentDestination, BalanceInfo } from '../types/payment.js';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Define tools with minimal descriptions
const createTools = (service: PaymanService) => [
  new DynamicTool({
    name: 'process_payment',
    description: 'Process a payment',
    func: async (input: string) => {
      const payment = await service.processPayment(JSON.parse(input));
      return JSON.stringify(payment);
    }
  }),
  new DynamicTool({
    name: 'check_payment_status', 
    description: 'Get payment status',
    func: async (id: string) => {
      const status = await service.getPaymentStatus(id);
      return JSON.stringify(status);
    }
  }),
  new DynamicTool({
    name: 'search_payees',
    description: 'Search payees',
    func: async (query: string) => {
      const payees = await service.searchPayees(query);
      return JSON.stringify(payees);
    }
  }),
  new DynamicTool({
    name: 'check_balance',
    description: 'Get balance',
    func: async () => {
      const balance = await service.getBalance();
      return JSON.stringify(balance);
    }
  })
];

// Simple agent factory with internal initialization
export async function createAgent() {
  // Validate OpenAI API key
  if (!process.env.OPENAI_API_KEY) {
    throw new Error('OPENAI_API_KEY is required');
  }

  // Initialize model
  const model = new ChatOpenAI({
    modelName: 'gpt-4',
    temperature: 0,
    openAIApiKey: process.env.OPENAI_API_KEY
  });

  // Initialize service
  const service = new PaymanService();

  // Initialize tools
  const tools = createTools(service);

  return {
    async processPayment(details: PaymentDetails) {
      const result = await tools[0].call(JSON.stringify(details));
      return JSON.parse(result) as PaymentStatus;
    },

    async checkPaymentStatus(id: string) {
      const result = await tools[1].call(id);
      return JSON.parse(result) as PaymentStatus;
    },

    async searchPayees(query: string) {
      const result = await tools[2].call(query);
      return JSON.parse(result) as PaymentDestination[];
    },

    async getBalance() {
      const result = await tools[3].call('');
      return JSON.parse(result) as BalanceInfo;
    }
  };
} 