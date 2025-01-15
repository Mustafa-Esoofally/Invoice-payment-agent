// In-memory store for processed emails
export const processedEmails = [];

// Maximum number of emails to keep in memory
const MAX_EMAILS = 100;

export function addEmail(email) {
  // Add to front of array
  processedEmails.unshift(email);
  
  // Keep only the latest MAX_EMAILS
  if (processedEmails.length > MAX_EMAILS) {
    processedEmails.pop();
  }
  
  return email;
} 