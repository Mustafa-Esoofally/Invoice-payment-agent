require('dotenv').config();
const mongoose = require('mongoose');
const Invoice = require('../models/Invoice');

const sampleInvoices = [
    {
        invoiceNumber: 'INV-2024-001',
        amount: 1500.00,
        currency: 'USD',
        recipientName: 'John Smith',
        accountNumber: '1234567890',
        bankDetails: {
            bankName: 'Chase Bank',
            routingNumber: '021000021',
            swiftCode: 'CHASUS33',
        },
        description: 'Consulting Services - January 2024',
        dueDate: new Date('2024-02-15'),
    },
    {
        invoiceNumber: 'INV-2024-002',
        amount: 2750.50,
        currency: 'USD',
        recipientName: 'Sarah Johnson',
        accountNumber: '9876543210',
        bankDetails: {
            bankName: 'Bank of America',
            routingNumber: '026009593',
            swiftCode: 'BOFAUS3N',
        },
        description: 'Web Development Project - Phase 1',
        dueDate: new Date('2024-02-20'),
    },
    {
        invoiceNumber: 'INV-2024-003',
        amount: 950.00,
        currency: 'USD',
        recipientName: 'Tech Solutions LLC',
        accountNumber: '5555666677',
        bankDetails: {
            bankName: 'Wells Fargo',
            routingNumber: '121000248',
            swiftCode: 'WFBIUS6S',
        },
        description: 'Software License Renewal',
        dueDate: new Date('2024-02-28'),
    },
];

async function generateSampleData() {
    try {
        await mongoose.connect(process.env.MONGODB_URI);
        console.log('Connected to MongoDB');

        // Clear existing invoices
        await Invoice.deleteMany({});
        console.log('Cleared existing invoices');

        // Insert sample invoices
        const result = await Invoice.insertMany(sampleInvoices);
        console.log(`Created ${result.length} sample invoices`);

        console.log('Sample data generation complete!');
    } catch (error) {
        console.error('Error generating sample data:', error);
    } finally {
        await mongoose.disconnect();
    }
}

generateSampleData(); 