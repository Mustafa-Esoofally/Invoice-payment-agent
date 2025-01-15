import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import dotenv from 'dotenv';
import GmailService from './gmail.js';
import { processedEmails, addEmail } from './emailStore.js';

dotenv.config();

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, {
  cors: {
    origin: "http://localhost:3000",
    methods: ["GET", "POST"]
  }
});

const port = 3001;
const gmailService = new GmailService();

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.get('/api/emails', (req, res) => {
  res.json(processedEmails);
});

// WebSocket connection
io.on('connection', (socket) => {
  console.log('Client connected');
  
  socket.on('disconnect', () => {
    console.log('Client disconnected');
  });
});

// Start server
httpServer.listen(port, async () => {
  console.log(`Server running at http://localhost:${port}`);
  
  // Initialize email directory
  await gmailService.initialize();
  
  // Try to authenticate using stored credentials
  const isAuthenticated = await gmailService.authenticate();
  
  if (isAuthenticated) {
    // If we have valid credentials, start watching the inbox
    await gmailService.watchInbox();
    
    // Override the email processing callback to emit socket events
    const originalProcessEmail = gmailService.processEmail.bind(gmailService);
    gmailService.processEmail = async (email) => {
      const processedEmail = await originalProcessEmail(email);
      
      // Store the email
      addEmail(processedEmail);
      
      // Emit to all connected clients
      io.emit('newEmail', processedEmail);
      
      return processedEmail;
    };
  }
}); 