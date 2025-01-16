import { ChatOpenAI } from '@langchain/openai';
import { DynamicTool } from '@langchain/core/tools';
import { AgentExecutor, createOpenAIFunctionsAgent } from 'langchain/agents';
import { ChatPromptTemplate, MessagesPlaceholder } from '@langchain/core/prompts';
import { SystemMessage } from '@langchain/core/messages';
import { PaymanService } from '../services/paymanService.js';
import { PaymentDetails } from '../types/payment.js';
import { generateCheckoutUrl } from '../services/paymanClient.js';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Create the invoice agent tools
const createInvoiceTools = (service: PaymanService) => [
  new DynamicTool({
    name: 'check_balance',
    description: 'Check the current available balance',
    func: async () => {
      const balance = await service.getBalance();
      return JSON.stringify({
        available: balance.available,
        currency: 'USD'
      });
    }
  }),
  new DynamicTool({
    name: 'search_payee',
    description: 'Search for a payee by name',
    func: async (input: string) => {
      const payees = await service.searchPayees(input);
      return JSON.stringify(payees || []);
    }
  }),
  new DynamicTool({
    name: 'process_payment',
    description: 'Process a payment with the given details',
    func: async (input: string) => {
      const details: PaymentDetails = JSON.parse(input);
      const payment = await service.processPayment(details);
      return JSON.stringify(payment);
    }
  }),
  new DynamicTool({
    name: 'check_payment_status',
    description: 'Check the status of a payment by ID',
    func: async (input: string) => {
      const status = await service.getPaymentStatus(input);
      return JSON.stringify(status);
    }
  }),
  new DynamicTool({
    name: 'generate_checkout_url',
    description: 'Generate a checkout URL to add funds',
    func: async (input: string) => {
      const { amount, currency, description, memo } = JSON.parse(input);
      const url = await generateCheckoutUrl(amount, currency, description, memo);
      return JSON.stringify({ checkoutUrl: url });
    }
  })
];

// Create the invoice agent
export async function createInvoiceAgent() {
  // Validate OpenAI API key
  if (!process.env.OPENAI_API_KEY) {
    throw new Error('OPENAI_API_KEY is required');
  }

  // Initialize the LLM
  const llm = new ChatOpenAI({
    modelName: 'gpt-4',
    temperature: 0,
  });

  // Create PaymanService instance
  const service = new PaymanService();

  // Create tools
  const tools = createInvoiceTools(service);

  // Create the prompt template
  const prompt = ChatPromptTemplate.fromMessages([
    new SystemMessage(`You are an AI invoice processing agent. Your task is to process invoice payments using the available tools.

Available tools:
- check_balance: Check current available balance
- search_payee: Search for a payee by name
- process_payment: Process a payment
- check_payment_status: Verify payment status
- generate_checkout_url: Generate URL for adding funds

For each invoice in the batch:
1. Check the available balance using check_balance
2. Validate the payment amount against the balance
3. Search for the payee using search_payee
4. If insufficient funds, generate a checkout URL using generate_checkout_url
5. If sufficient funds and payee found, process the payment using process_payment
6. Verify the payment status using check_payment_status

After processing each invoice, provide a summary in this format:

=== Invoice [ID] ===
📄 Invoice Details:
- Invoice Number: [number]
- Recipient: [name]
- Amount: $[amount] [currency]
- Description: [description]

💳 Processing Results:
- Status: [success/failed]
- Payment ID: [id]
- Reference: [reference]
- Timestamp: [timestamp]

💰 Balance:
- Previous: $[amount] [currency]
- Payment: $[amount] [currency]
- Current: $[amount] [currency]

If there are any errors, show them under:
❌ Errors:
- [error details]

For insufficient funds, show:
💳 Add Funds:
- Amount Needed: $[amount]
- Checkout URL: [url]

=== End Invoice [ID] ===

After all invoices are processed, provide a final summary:

=== Batch Summary ===
📊 Results:
- Total Invoices: [count]
- Successful: [count]
- Failed: [count]
- Total Amount Processed: $[amount]
- Total Amount Pending: $[amount]

💰 Final Balance: $[amount] [currency]
=== End Summary ===

Important:
1. Format all amounts with 2 decimal places (e.g., $1,234.56)
2. Include commas in large numbers (e.g., $1,234,567.89)
3. Show timestamps in local time (e.g., 2024-01-16 15:05:07)
4. Keep error messages concise and clear
5. For failed payments, clearly indicate the reason
6. For insufficient funds, show the exact amount needed and checkout URL`),
    ["human", `Please process these invoices:

Invoices: {input}

Process each invoice in sequence, checking balance and validating before each payment.`],
    new MessagesPlaceholder("agent_scratchpad")
  ]);

  // Create the agent
  const agent = await createOpenAIFunctionsAgent({
    llm,
    tools,
    prompt
  });

  // Create the executor
  const agentExecutor = new AgentExecutor({
    agent,
    tools,
    verbose: true
  });

  return {
    // Process a batch of invoices
    async processBatch(invoices: any) {
      const result = await agentExecutor.invoke({
        input: JSON.stringify(invoices, null, 2)
      });
      return result;
    },

    // Get the underlying service for direct operations
    getService() {
      return service;
    }
  };
} 