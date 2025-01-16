import { createInvoiceAgent } from '../agents/invoiceAgent.js';
import samplePayments from './samplePayments.json' assert { type: "json" };
import fs from 'fs';
import path from 'path';

async function testInvoiceAgent() {
  try {
    console.log('\n=== Starting Invoice Processing Test ===\n');
    
    const agent = await createInvoiceAgent();
    
    console.log('Processing batch of invoices...\n');
    const result = await agent.processBatch(samplePayments.payments);
    
    // Format and display the result
    if (typeof result.output === 'string') {
      console.log(result.output);
      
      // Save to file
      const paymentDetailsPath = path.join(process.cwd(), 'payment_details.txt');
      fs.appendFileSync(paymentDetailsPath, '\n' + result.output + '\n');
      console.log('\nPayment details have been saved to payment_details.txt');
    } else {
      console.log(JSON.stringify(result.output, null, 2));
    }
    
    console.log('\n=== Invoice Processing Test Complete ===\n');
  } catch (err: any) {
    console.error('\n❌ Test failed with error:', err.message);
    process.exit(1);
  }
}

testInvoiceAgent().catch((err: any) => {
  console.error('Failed to run test:', err.message);
  process.exit(1);
}); 