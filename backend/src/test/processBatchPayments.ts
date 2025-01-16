import { createAgent } from '../agents/paymentAgent.js';
import samplePayments from './samplePayments.json' assert { type: "json" };
import { generateCheckoutUrl } from '../services/paymanClient.js';

async function processBatchPayments() {
  console.log('\n🏁 Starting batch payment processing...');
  const agent = await createAgent();

  for (const payment of samplePayments.payments) {
    // Check current balance before each payment
    const balance = await agent.getBalance();
    const balanceInDollars = balance.available;
    
    console.log(`\n📝 Processing payment ${payment.id}:`);
    console.log(`Recipient: ${payment.recipientName}`);
    console.log(`Amount: $${payment.amount.toFixed(2)} ${payment.currency}`);
    console.log(`Current balance: $${balance.available}\n`);

    // Compare dollars with dollars
    if (balanceInDollars < payment.amount) {
      console.log('⚠️ Insufficient funds for payment.');
      const requiredAmount = (payment.amount - balanceInDollars).toFixed(2);
      console.log(`Additional funds needed: $${requiredAmount} USD`);
      
      // Generate checkout URL for the required amount
      try {
        const checkoutUrl = await generateCheckoutUrl(
          Number(requiredAmount),
          'USD',
          'Add funds for batch payments',
          'Batch payment processing'
        );
        console.log(`💳 Add funds: ${checkoutUrl}\n`);
      } catch (error) {
        console.error('❌ Error generating checkout URL:', error);
      }
      
      console.log('Skipping this payment until funds are available.\n');
      continue;
    }

    console.log('\nSearching for payee:', payment.recipientName);
    const payees = await agent.searchPayees(payment.recipientName);
    
    if (!payees || payees.length === 0) {
      console.error(`❌ No payee found for ${payment.recipientName}`);
      continue;
    }

    // Send payment details with amount in dollars
    const paymentDetails = {
      amount: payment.amount, // Send the original dollar amount
      currency: payment.currency,
      payeeId: payees[0].id,
      description: payment.description,
      email: payment.customerEmail,
      memo: payment.memo,
      recipientName: payment.recipientName
    };

    console.log('Payment details:', paymentDetails);

    try {
      const result = await agent.processPayment(paymentDetails);
      console.log('✅ Payment processed successfully');
      console.log('Payment ID:', result.id);
      
      // Verify payment status
      const status = await agent.checkPaymentStatus(result.id);
      console.log('Payment status:', status);
      
      // Get updated balance after payment
      const newBalance = await agent.getBalance();
      console.log(`New balance: $${(newBalance.available/100).toFixed(2)} USD\n`);
    } catch (error) {
      console.error('❌ Error processing payment:', error);
      continue;
    }
  }

  console.log('\n✅ Batch payment processing completed');
}

// Run the batch payment process
processBatchPayments().then(() => {
  console.log('\n🎉 All payments processed successfully!');
  process.exit(0);
}).catch(error => {
  console.error('\n❌ Batch processing failed:', error);
  process.exit(1);
}); 