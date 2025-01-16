import { ChatOpenAI } from '@langchain/openai';
import { DynamicTool } from '@langchain/core/tools';
import { AgentExecutor, createOpenAIFunctionsAgent } from 'langchain/agents';
import { ChatPromptTemplate, MessagesPlaceholder } from '@langchain/core/prompts';
import { PaymanService } from '../services/paymanService.js';
import { PaymentDetails } from '../types/payment.js';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Create the invoice agent tools
const createInvoiceTools = (service: PaymanService) => [
  new DynamicTool({
    name: 'validate_and_process_payment',
    description: 'Validate and process a payment',
    func: async (input: string) => {
      const data = JSON.parse(input);
      
      // First check balance
      const balance = await service.getBalance();
      if (balance.available < data.amount) {
        return JSON.stringify({
          success: false,
          error: 'Insufficient funds',
          required: data.amount,
          available: balance.available
        });
      }

      // Search for payee
      const payees = await service.searchPayees(data.recipientName);
      if (!payees || payees.length === 0) {
        return JSON.stringify({
          success: false,
          error: 'Payee not found',
          recipientName: data.recipientName
        });
      }

      // Process payment
      const paymentDetails: PaymentDetails = {
        amount: data.amount,
        currency: data.currency,
        payeeId: payees[0].id,
        description: data.description,
        email: data.customerEmail,
        memo: data.memo,
        recipientName: data.recipientName
      };

      try {
        const payment = await service.processPayment(paymentDetails);
        return JSON.stringify({
          success: true,
          payment,
          payee: payees[0],
          balance: await service.getBalance()
        });
      } catch (error) {
        return JSON.stringify({
          success: false,
          error: error instanceof Error ? error.message : String(error)
        });
      }
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
    ["system", `You are an AI invoice processing agent. Your task is to process invoice payments.

For each invoice:
1. Validate that all required fields are present:
   - invoiceNumber
   - recipientName
   - amount
   - currency
   - description
   - customerEmail
2. Use validate_and_process_payment to process the payment
3. Provide a clear summary of the results

After processing, provide a summary in this format:
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

If there are any errors, show them clearly under an ❌ Errors section.`],
    ["human", `Please process this invoice:

Invoice: {input}

Validate the invoice and process the payment if valid.`],
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
    // Process a single invoice
    async processInvoice(invoice: any) {
      const result = await agentExecutor.invoke({
        input: JSON.stringify(invoice, null, 2)
      });
      return result;
    },

    // Process multiple invoices
    async processBatch(invoices: any[]) {
      const results = [];
      for (const invoice of invoices) {
        try {
          const result = await this.processInvoice(invoice);
          results.push({
            invoice,
            result,
            success: true
          });
        } catch (error) {
          results.push({
            invoice,
            error: error instanceof Error ? error.message : String(error),
            success: false
          });
        }
      }
      return results;
    },

    // Get the underlying service for direct operations
    getService() {
      return service;
    }
  };
} 