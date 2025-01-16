import { createAgent } from '../agents/paymentAgent.js';
import { PaymentDetails } from '../types/payment.js';
import samplePayments from './samplePayments.json' assert { type: "json" };

async function main() {
  const agent = await createAgent();

  try {
    // Test balance check to ensure sufficient funds
    console.log('\nChecking balance...');
    const balance = await agent.getBalance();
    console.log('Balance:', balance);

    // Get sample payment data
    const samplePayment = samplePayments.payments[0];

    // Test payee search with actual recipient name
    console.log('\nSearching for payee:', samplePayment.recipientName);
    const payees = await agent.searchPayees(samplePayment.recipientName);
    console.log('Found payees:', payees);

    if (!payees.length) {
      throw new Error(`No payee found matching ${samplePayment.recipientName}`);
    }

    // Use a smaller test amount first (100 cents = $1.00)
    const testAmount = 100; // $1.00 test payment
    console.log(`\nTesting with smaller amount: $${testAmount/100}`);

    // Process the actual payment
    console.log('\nProcessing payment...');
    const paymentDetails: PaymentDetails = {
      amount: testAmount,
      currency: samplePayment.currency,
      payeeId: payees[0].id,
      description: 'Test payment - small amount',
      email: samplePayment.customerEmail
    };
    console.log('Payment details:', paymentDetails);
    
    const payment = await agent.processPayment(paymentDetails);
    console.log('Payment processed:', payment);

    // Verify payment status
    console.log('\nVerifying payment status...');
    const status = await agent.checkPaymentStatus(payment.id);
    console.log('Payment status:', status);

    // Verify updated balance
    console.log('\nChecking updated balance...');
    const newBalance = await agent.getBalance();
    console.log('New balance:', newBalance);
    console.log('Balance change:', balance.available - newBalance.available);

    console.log('\n✅ Payment processed successfully');
  } catch (error) {
    console.error('\n❌ Payment processing error:', error);
    process.exit(1);
  }
}

main().catch(error => {
  console.error('\n❌ Fatal error:', error);
  process.exit(1);
}); 