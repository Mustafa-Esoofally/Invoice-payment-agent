import { OpenAIToolSet } from 'composio-core';
import { ChatOpenAI } from '@langchain/openai';
import { AgentExecutor, createOpenAIFunctionsAgent } from 'langchain/agents';
import { HumanMessage, SystemMessage } from '@langchain/core/messages';
import { DynamicStructuredTool } from '@langchain/core/tools';
import { ChatPromptTemplate, MessagesPlaceholder } from '@langchain/core/prompts';
import { z } from 'zod';

const COMPOSIO_API_KEY = process.env.COMPOSIO_API_KEY;
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

interface EmailRequest {
  connectedAccountId: string;
  maxResults?: number;
  pageToken?: string;
  includeSpamTrash?: boolean;
}

// Define the schema for the tool's input
const GmailFetchEmailsSchema = z.object({
  user_id: z.string().default('me').describe("The user's email address or 'me' for the authenticated user."),
  max_results: z.number().optional().describe('Maximum number of messages to return.'),
  page_token: z.string().optional().describe('Page token to retrieve a specific page of results.'),
  include_spam_trash: z.boolean().optional().describe('Include messages from SPAM and TRASH in the results.')
});

export async function getEmailsWithAgent(request: EmailRequest) {
  if (!COMPOSIO_API_KEY || !OPENAI_API_KEY) {
    throw new Error('Missing required API keys');
  }

  // Initialize OpenAI LLM
  const llm = new ChatOpenAI({
    openAIApiKey: OPENAI_API_KEY,
    modelName: 'gpt-4',
    temperature: 0
  });

  // Initialize Composio toolset
  const composioToolset = new OpenAIToolSet({ apiKey: COMPOSIO_API_KEY });

  // Create the Gmail fetch emails tool
  const gmailFetchEmailsTool = new DynamicStructuredTool({
    name: 'GMAIL_FETCH_EMAILS',
    description: 'Fetch emails from Gmail with specified parameters',
    schema: GmailFetchEmailsSchema,
    func: async ({ user_id, max_results, page_token, include_spam_trash }) => {
      const response = await composioToolset.actions.execute({
        actionName: 'GMAIL_FETCH_EMAILS',
        requestBody: {
          connectedAccountId: request.connectedAccountId,
          appName: 'gmail',
          input: {
            user_id,
            max_results,
            page_token,
            include_spam_trash,
            format: 'full'
          }
        }
      });
      return response.data;
    }
  });

  const tools = [gmailFetchEmailsTool];

  // Create the prompt template with agent_scratchpad
  const prompt = ChatPromptTemplate.fromMessages([
    new SystemMessage(`
      You are a helpful assistant that fetches and processes Gmail emails.
      Your task is to:
      1. Fetch emails using the GMAIL_FETCH_EMAILS tool
      2. Process each email to extract:
         - Subject (from headers)
         - Snippet (clean and format the text)
         - Label IDs (categorize and format)
         - Attachment information (detect and list all attachments)
      3. Format the response as a clean JSON structure
      4. Handle any errors gracefully
    `),
    new HumanMessage("{input}"),
    new MessagesPlaceholder("agent_scratchpad")
  ]);

  // Create the agent
  const agent = await createOpenAIFunctionsAgent({
    llm,
    tools,
    prompt
  });

  // Create the agent executor
  const agentExecutor = AgentExecutor.fromAgentAndTools({
    agent,
    tools,
    verbose: true,
    handleParsingErrors: true // Add error handling for message parsing
  });

  // Prepare the task description
  const task = `Fetch and process Gmail emails with the following parameters:
    - Connected Account ID: ${request.connectedAccountId}
    - Max Results: ${request.maxResults || 10}
    - Page Token: ${request.pageToken || 'none'}
    - Include Spam/Trash: ${request.includeSpamTrash || false}
    
    For each email, please:
    1. Extract the subject from email headers
    2. Clean and format the snippet text
    3. Process label IDs and categorize them
    4. Detect attachments and provide:
       - Filename
       - MIME type
       - Attachment ID
    5. Format everything in a clean JSON structure
    6. Include the nextPageToken if available

    Return the processed emails in a format that's easy for the frontend to consume.`;

  // Execute the task
  const result = await agentExecutor.invoke({
    input: task
  });

  return result;
} 