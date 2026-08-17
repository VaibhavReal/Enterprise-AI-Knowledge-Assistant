# Financial Domain Concepts for RAG Engineers

When building a Retrieval-Augmented Generation (RAG) system for financial research, understanding the terminology is critical. The way a user asks a question dictates how the system must retrieve the data. This guide covers core financial concepts, where they live in documents, and how RAG should handle them.

## 1. Profitability Metrics

### Revenue (Top Line)
*   **Definition**: The total amount of money brought in by a company's operations, before any expenses are deducted. Also called "Sales" or "Top Line."
*   **Example**: "Our software subscriptions generated $50 million in revenue."
*   **Where in documents**: Income Statement, Financial Highlights, Management Discussion & Analysis (MD&A).
*   **RAG Retrieval**: Users might search for "sales," "top line," or "total income." Hybrid search (BM25) helps match the specific terminology used by the company (e.g., "Net Revenue" vs. "Gross Revenue").

### Gross Profit
*   **Definition**: Revenue minus the Cost of Goods Sold (COGS). It represents the profit made after paying for the direct costs of producing the goods or services.
*   **Example**: $50M Revenue - $20M Server Costs = $30M Gross Profit.
*   **Where in documents**: Income Statement.

### Operating Profit / EBIT (Earnings Before Interest and Taxes)
*   **Definition**: Gross profit minus operating expenses (like salaries, rent, marketing). It shows how much profit a company makes from its core business operations.
*   **Example**: "Operating profit stood at $15 million after adjusting for R&D expenses."
*   **Where in documents**: Income Statement.
*   **RAG Retrieval**: This metric goes by many names. The dense embedding model must understand that "EBIT" and "Operating Income" refer to the same concept.

### EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization)
*   **Definition**: A proxy for a company's operating cash flow. It strips out non-cash expenses (like depreciation of servers) and financing decisions (interest/taxes).
*   **Example**: "Adjusted EBITDA grew by 12% to $25 million."
*   **Where in documents**: Often highlighted in press releases, MD&A, or non-GAAP reconciliations. Not a standard GAAP line item.

### Net Income (Bottom Line)
*   **Definition**: The final profit after all expenses, interest, and taxes have been paid.
*   **Where in documents**: The final line of the Income Statement.
*   **RAG Retrieval**: Queries often ask for "profits." The RAG system must retrieve context that clarifies whether the document means Gross Profit or Net Income.

### EPS (Earnings Per Share)
*   **Definition**: Net income divided by the number of outstanding shares. Tells an investor how much profit is attached to each share of stock.
*   **Where in documents**: Bottom of the Income Statement, prominent in Earnings Releases.

## 2. Margin Metrics (Ratios)

### Operating Margin / Net Margin
*   **Definition**: Profitability expressed as a percentage of revenue.
    *   Operating Margin = Operating Profit / Revenue
    *   Net Margin = Net Income / Revenue
*   **Example**: "Our operating margin improved to 20% due to cost-cutting."
*   **RAG Retrieval**: RAG systems must be careful not to confuse absolute numbers ($20M) with margins (20%). The prompt must instruct the LLM to preserve the '%' sign exactly as it appears in the text.

## 3. Cash and Capital

### Free Cash Flow (FCF)
*   **Definition**: The cash a company generates after accounting for cash outflows to support operations and maintain its capital assets. It's the cash left over to pay dividends, buy back stock, or pay down debt.
*   **Where in documents**: Cash Flow Statement.

### Capital Expenditure (CapEx)
*   **Definition**: Money spent by a business to acquire, maintain, or upgrade physical assets (property, plants, equipment, technology).
*   **Example**: "We invested $5M in CapEx to build a new data center."
*   **Where in documents**: Cash Flow Statement (under Investing Activities), MD&A.

## 4. Balance Sheet Metrics

### Debt vs. Cash
*   **Long-term Debt**: Money owed that is due in more than one year.
*   **Short-term Debt**: Money owed that is due within one year.
*   **Cash & Equivalents**: Cash on hand or assets easily converted to cash.
*   **Where in documents**: Balance Sheet.
*   **RAG Retrieval**: Questions about a company's "leverage" or "runway" require retrieving debt and cash positions together.

### Working Capital
*   **Definition**: Current Assets minus Current Liabilities. Measures a company's short-term financial health and operational efficiency.

## 5. Document Types and Sections

### Annual Reports (10-K)
*   Comprehensive, audited yearly reports. Contains detailed financials, risk factors, and management's view of the business.
*   **RAG Note**: These are massive (100+ pages). Retrieval precision is tested heavily here.

### Earnings Reports (10-Q / Press Releases)
*   Quarterly updates. Usually shorter, focusing on immediate performance against expectations.

### Risk Factors
*   A specific section in filings where management outlines everything that could go wrong (competition, regulation, supply chain).
*   **RAG Note**: This text is usually dense and qualitative. Semantic search (dense embeddings) shines here when users ask abstract questions like "What geopolitical risks is the company facing?"

### Guidance / Outlook
*   **Definition**: Management's forecast or expectations for the next quarter or year's financial performance.
*   **Example**: "We expect Q3 revenue to be in the range of $50M to $55M."
*   **RAG Retrieval**: This is crucial for investors. RAG must distinguish between historical facts ("Revenue was $50M") and forward-looking statements ("Revenue is expected to be $50M"). The chunk metadata (identifying the section as "Outlook") is vital here.
