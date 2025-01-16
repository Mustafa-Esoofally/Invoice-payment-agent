export interface PaymentDetails {
  amount: number;
  currency: string;
  payeeId: string;
  routingNumber?: string;
  description?: string;
  email?: string;
  phoneNumber?: string;
  address?: string;
  customerId?: string;
  memo?: string;
  recipientName?: string;
}

export interface PaymentStatus {
  id: string;
  status: 'pending' | 'completed' | 'failed';
  amount: number;
  currency: string;
  timestamp: string;
}

export interface PaymentDestination {
  id: string;
  name: string;
  email: string;
  routingNumber: string;
  accountType: string;
}

export interface BalanceInfo {
  available: number;
  currency: string;
  pending?: number;
} 