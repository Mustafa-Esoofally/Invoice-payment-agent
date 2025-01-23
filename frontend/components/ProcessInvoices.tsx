import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";

interface ProcessInvoicesProps {
  isProcessing: boolean;
  onProcess: () => void;
}

export function ProcessInvoices({ isProcessing, onProcess }: ProcessInvoicesProps) {
  return (
    <Button 
      className="w-full bg-black hover:bg-gray-800" 
      onClick={onProcess}
      disabled={isProcessing}
    >
      <RefreshCw className={`mr-2 h-4 w-4 ${isProcessing ? 'animate-spin' : ''}`} />
      {isProcessing ? 'Processing Invoices...' : 'Process Invoices'}
    </Button>
  );
} 