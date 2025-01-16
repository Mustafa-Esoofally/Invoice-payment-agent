import dotenv from 'dotenv';
import { PaymentAgent } from '../agents/paymentAgent.js';
import paymanService from '../services/paymanService.js';

dotenv.config();

const invoice = {
    invoiceNumber: "INV-2024-001",
    amount: 2500.00,
    currency: "USD",
    recipientName: "Tech Consulting Services",
    accountNumber: "1234567890",
    routingNumber: "021000021",
    description: "Technical consulting services - Q1 2024",
    dueDate: "2024-02-15",
    items: [
        {
            description: "Software Architecture Consulting",
            amount: 1500.00,
            hours: 10
        },
        {
            description: "Code Review Services",
            amount: 1000.00,
            hours: 8
        }
    ]
};

async function testDirectPayment() {
    console.log('\n🧪 Testing direct payment through PaymanService...');
    try {
        const payment = await paymanService.processPayment({
            amount: invoice.amount,
            currency: invoice.currency,
            recipientName: invoice.recipientName,
            accountNumber: invoice.accountNumber,
            routingNumber: invoice.routingNumber,
            description: invoice.description
        });
        console.log('✅ Direct payment successful:', payment);
        return payment;
    } catch (error) {
        console.error('❌ Direct payment failed:', error.message);
        throw error;
    }
}

async function processInvoicePayment() {
    try {
        console.log('\n📋 Starting Invoice Payment Process...');
        console.log('Invoice Details:', JSON.stringify(invoice, null, 2));

        // First try direct payment
        const directPayment = await testDirectPayment();
        
        if (directPayment) {
            console.log('\n🚀 Now testing with AI Payment Agent...');
            const agent = await new PaymentAgent().initialize();
            console.log('✅ Agent initialized successfully');

            // Check balance
            console.log('\n💰 Checking available balance...');
            const balanceResult = await agent.getBalance();
            console.log('Balance:', balanceResult);

            // Search payee
            console.log('\n🔍 Searching for existing payee...');
            const searchResult = await agent.searchPayees(invoice.recipientName);
            console.log('Payee search results:', searchResult);

            // Process payment through agent
            console.log('\n💸 Processing invoice payment through agent...');
            const paymentResult = await agent.processPayment(invoice);
            console.log('\n✅ Payment processing result:', paymentResult);
        }

    } catch (error) {
        console.error('\n❌ Error processing invoice:', error.message);
        console.error('Stack trace:', error.stack);
        process.exit(1);
    }
}

// Run the invoice payment process
processInvoicePayment().then(() => {
    console.log('\n✅ Invoice payment process completed');
    process.exit(0);
}).catch(error => {
    console.error('\n❌ Invoice payment failed:', error);
    process.exit(1);
}); 