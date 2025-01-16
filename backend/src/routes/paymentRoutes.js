import express from 'express';
import { PaymentAgent } from '../agents/paymentAgent.js';

const router = express.Router();
let paymentAgent;

// Initialize the payment agent
(async () => {
    paymentAgent = await new PaymentAgent().initialize();
})();

// Process a payment
router.post('/process', async (req, res) => {
    try {
        const paymentDetails = req.body;
        const result = await paymentAgent.processPayment(paymentDetails);
        res.json({ success: true, result });
    } catch (error) {
        console.error('Error processing payment:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Check payment status
router.get('/status/:paymentId', async (req, res) => {
    try {
        const { paymentId } = req.params;
        const status = await paymentAgent.checkPaymentStatus(paymentId);
        res.json({ success: true, status });
    } catch (error) {
        console.error('Error checking payment status:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Search payees
router.get('/payees/search', async (req, res) => {
    try {
        const { query } = req.query;
        const result = await paymentAgent.searchPayees(query);
        res.json({ success: true, result });
    } catch (error) {
        console.error('Error searching payees:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Get balance
router.get('/balance', async (req, res) => {
    try {
        const result = await paymentAgent.getBalance();
        res.json({ success: true, result });
    } catch (error) {
        console.error('Error getting balance:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

export default router; 