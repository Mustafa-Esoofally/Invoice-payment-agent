import dotenv from 'dotenv';
import { PaymentAgent } from '../agents/paymentAgent.js';

// Load environment variables before anything else
dotenv.config();

// Verify environment variables are loaded
console.log('\nEnvironment Check:');
console.log('PAYMAN_API_SECRET:', process.env.PAYMAN_API_SECRET ? 'Present' : 'Missing');
console.log('OPENAI_API_KEY:', process.env.OPENAI_API_KEY ? 'Present' : 'Missing');
console.log('NODE_ENV:', process.env.NODE_ENV || 'Not set');
console.log('PAYMAN_BASE_URL:', process.env.PAYMAN_BASE_URL || 'Not set');

async function runTest(testName, testFn) {
    console.log(`\n🧪 Running ${testName}...`);
    try {
        await testFn();
        console.log(`✅ ${testName} completed successfully`);
    } catch (error) {
        console.error(`❌ ${testName} failed:`, error);
        throw error; // Re-throw to stop further tests
    }
}

async function testPaymentAgent() {
    try {
        console.log('\n🚀 Initializing Payment Agent...');
        const agent = await new PaymentAgent().initialize();
        console.log('✅ Agent initialized successfully');

        await runTest('Balance Check', async () => {
            const balance = await agent.getBalance();
            console.log('Balance:', balance);
        });

        await runTest('Payee Search', async () => {
            const searchResult = await agent.searchPayees('tech');
            console.log('Search Results:', searchResult);
        });

        const paymentDetails = {
            amount: 1500.00,
            recipientName: "Tech Solutions LLC",
            accountNumber: "1234567890",
            bankDetails: {
                routingNumber: "021000021"
            },
            description: "Software development services - January 2024"
        };

        let paymentId;
        await runTest('Payment Processing', async () => {
            console.log('Payment Details:', JSON.stringify(paymentDetails, null, 2));
            const paymentResult = await agent.processPayment(paymentDetails);
            console.log('Payment Result:', paymentResult);
            paymentId = paymentResult.match(/Payment ID: (.+)$/)?.[1];
        });

        if (paymentId) {
            await runTest('Payment Status Check', async () => {
                const statusResult = await agent.checkPaymentStatus(paymentId);
                console.log('Status Result:', statusResult);
            });
        }

        await runTest('Complex Payment Scenario', async () => {
            const result = await agent.executor.invoke({
                input: `I need to make a payment of $2,500 to John Smith (Account: 9876543210, Routing: 026009593) 
                       for consulting services, but first check if we have sufficient balance and if there's any 
                       existing payee with similar details to avoid duplication.`
            });
            console.log('Complex Scenario Result:', result.output);
        });

    } catch (error) {
        console.error('\n❌ Test suite failed:', error);
        process.exit(1);
    }
}

// Run the tests
console.log('\n🚀 Starting Payment Agent Test Suite...');
testPaymentAgent().then(() => {
    console.log('\n✅ All tests completed successfully');
}).catch(error => {
    console.error('\n❌ Test suite failed:', error);
    process.exit(1);
}); 