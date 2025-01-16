import { createInvoiceAgent } from '../agents/invoiceAgent.js';

// Sample invoice data
const sampleInvoice = {
  invoiceNumber: 'INV-2024-001',
  date: '2024-01-16',
  dueDate: '2024-02-15',
  recipientName: 'Tech Consulting Services',
  description: 'Q1 2024 Software Development Services',
  amount: 2670.00,
  currency: 'USD',
  customerEmail: 'billing@techconsulting.com',
  memo: 'Q1 2024 Development',
  lineItems: [
    {
      description: 'Software Development',
      hours: 89,
      rate: 30,
      amount: 2670.00
    }
  ]
};

async function main() {
  try {
    console.log('\n🤖 Creating invoice processing agent...');
    const agent = await createInvoiceAgent();

    console.log('\n📄 Processing sample invoice...');
    const result = await agent.processInvoice(sampleInvoice);
    console.log('\n✅ Processing result:', JSON.stringify(result, null, 2));

    // Test batch processing
    console.log('\n📚 Testing batch processing...');
    const batchResults = await agent.processBatch([
      sampleInvoice,
      {
        ...sampleInvoice,
        invoiceNumber: 'INV-2024-002',
        amount: 1.00,
        description: 'Test Invoice',
        memo: 'Small test payment'
      }
    ]);

    console.log('\n✅ Batch processing results:', JSON.stringify(batchResults, null, 2));

  } catch (error) {
    console.error('\n❌ Error:', error);
    process.exit(1);
  }
}

// Run the test
main().then(() => {
  console.log('\n✅ Test completed successfully');
  process.exit(0);
}).catch(error => {
  console.error('\n❌ Test failed:', error);
  process.exit(1);
}); 