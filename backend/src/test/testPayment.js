import dotenv from 'dotenv';
import { Paymanai } from "paymanai";

dotenv.config();

async function testPayment() {
    try {
        console.log('\n🚀 Starting Payman payment test...');
        console.log('API Secret:', process.env.PAYMAN_API_SECRET ? '✅ Found' : '❌ Missing');
        console.log('Base URL:', process.env.PAYMAN_BASE_URL ? '✅ Found' : '❌ Missing');
        
        // Initialize client
        const client = new Paymanai({
            xPaymanAPISecret: process.env.PAYMAN_API_SECRET,
            baseURL: process.env.PAYMAN_BASE_URL
        });
        console.log('✅ Client initialized');
        console.log('Client methods:', Object.keys(client));
        console.log('Payment methods:', client.payments ? Object.keys(client.payments) : '❌ No payments object');

        // Search for existing destinations
        console.log('\n🔍 Searching for all payment destinations...');
        const allDestinations = await client.payments.searchDestinations();
        console.log(`Found ${allDestinations.length} destinations`);

        // Optional: Search with filters
        console.log('\n🔍 Searching for specific payment destinations...');
        const filteredDestinations = await client.payments.searchDestinations({
            name: "Test Company",
            type: "US_ACH"
        });
        console.log(`Found ${filteredDestinations.length} matching destinations`);

        // Send payment as shown in docs
        console.log('\n💸 Sending test payment...');
        const timestamp = new Date().getTime();
        const paymentResponse = await client.payments.sendPayment({
            amountDecimal: 50.0,
            customerEmail: `test+${timestamp}@example.com`,
            customerName: `Test Customer ${timestamp}`,
            memo: `Test payment ${timestamp}`,
            paymentDestination: {
                type: "US_ACH",
                accountHolderName: `Test Company ${timestamp}`,
                accountNumber: "123456789",
                accountType: "checking",
                routingNumber: "021000021",
                name: `Test Company ${timestamp}`,
                contactDetails: {
                    contactType: "business",
                    email: `test+${timestamp}@example.com`,
                    phoneNumber: "+1234567890",
                    address: "123 Test St, City, State 12345"
                }
            }
        });
        
        // Parse the response if it's a string
        const response = typeof paymentResponse === 'string' ? JSON.parse(paymentResponse) : paymentResponse;
        console.log('\n✅ Payment response:', response);
        console.log('\n✅ Payment sent successfully:', {
            reference: response.reference,
            timestamp: new Date().toISOString()
        });

    } catch (error) {
        console.error('\n❌ Error:', error.message);
        console.error('Error stack:', error.stack);
        if (error.response?.data) {
            console.error('API Error details:', error.response.data);
        }
        if (error.cause) {
            console.error('Error cause:', error.cause);
        }
    }
}

// Run the test
console.log('\n📋 Starting payment test...');
testPayment().catch(error => {
    console.error('Test failed:', error);
    process.exit(1);
}); 