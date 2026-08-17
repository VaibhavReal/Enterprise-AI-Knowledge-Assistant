from __future__ import annotations

import re
from pathlib import Path

class FinancialMetadataExtractor:
    """
    Intelligent financial document metadata extractor.
    
    Automatically parses the first pages and filename to extract:
    - Company Name (SEC registrant format, title patterns, clean names)
    - Ticker Symbol (e.g. AAPL, MSFT, TSLA, RELIANCE)
    - Document Type (10-K, 10-Q, 8-K, Annual Report, Earnings Transcript, etc.)
    - Reporting Period (Q1, Q2, Q3, Q4, FY2024, Full Year)
    - Fiscal Year (e.g. 2024, 2023)
    """

    DOCUMENT_TYPE_MAP = [
        (r"\b10-?k\b|annual\s+report|form\s+10-k", "10-K (Annual Report)"),
        (r"\b10-?q\b|quarterly\s+report|form\s+10-q", "10-Q (Quarterly Report)"),
        (r"\b8-?k\b|current\s+report|form\s+8-k", "8-K (Current Report)"),
        (r"earnings\s+(?:call|release|conference|transcript)", "Earnings Call Transcript"),
        (r"investor\s+(?:presentation|deck|day)", "Investor Presentation"),
        (r"financial\s+statement|balance\s+sheet", "Financial Statements"),
    ]

    def extract_from_text(self, text: str, filename: str) -> dict:
        """
        Performs multi-pattern extraction across the document's header text and filename.
        """
        extracted = {}
        
        # 1. Detect Company Name
        company = self.detect_company_name(text, filename)
        if company:
            extracted["company_name"] = company

        # 2. Detect Ticker Symbol
        ticker = self.detect_ticker(text, filename)
        if ticker:
            extracted["ticker"] = ticker

        # 3. Detect Document Type
        doc_type = self.detect_document_type(text, filename)
        if doc_type:
            extracted["document_type"] = doc_type

        # 4. Detect Reporting Period
        period = self.detect_reporting_period(text, filename)
        if period:
            extracted["reporting_period"] = period

        # 5. Detect Fiscal Year
        year = self.detect_fiscal_year(text, filename)
        if year:
            extracted["fiscal_year"] = year

        return extracted

    def detect_company_name(self, text: str, filename: str) -> str | None:
        """
        Extracts company name from common SEC filing headers or document title lines.
        """
        # SEC Registrant pattern: (Exact name of registrant as specified in its charter)
        sec_pattern = r"(?:Exact\s+name\s+of\s+registrant\s+as\s+specified\s+in\s+its\s+charter[^\n]*\n+)\s*([A-Z0-9\s,\.\-&]+(?:INC|CORP|CORPORATION|LTD|LIMITED|LLC|PLC|CO|COMPANY|GROUP))"
        match = re.search(sec_pattern, text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if 3 < len(candidate) < 60:
                return candidate.title()

        # Check line above or below 'ANNUAL REPORT' or 'FORM 10-K'
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for idx, line in enumerate(lines[:15]):
            if re.search(r"\b(Inc\.|Corporation|Corp\.|Limited|Ltd\.|Holdings|Group|Company)\b", line, re.IGNORECASE):
                if len(line) < 60 and not re.search(r"Commission|Securities|Exchange|Act|Washington", line, re.IGNORECASE):
                    return line

        # Try clean filename parsing (e.g., 'Apple_10K_2024.pdf' -> 'Apple')
        stem = Path(filename).stem
        parts = re.split(r"[_\-\s]+", stem)
        if parts and len(parts[0]) > 2 and not parts[0].isdigit():
            # If the first word looks like a company name
            candidate = parts[0]
            if candidate.upper() not in ["FORM", "10K", "10Q", "ANNUAL", "REPORT", "Q1", "Q2", "Q3", "Q4", "FY24", "FY23"]:
                return candidate.replace("_", " ").title()

        return None

    def detect_ticker(self, text: str, filename: str) -> str | None:
        """Extract ticker symbol like AAPL, MSFT, TSLA."""
        # Check text: '(Trading Symbol: AAPL)', '(NASDAQ: AAPL)', '(NYSE: MSFT)'
        m = re.search(r"\b(?:NASDAQ|NYSE|Trading\s+Symbol|Ticker)[:\s]+([A-Z]{1,5})\b", text)
        if m:
            return m.group(1).upper()

        # Check filename for ticker at start, e.g., 'AAPL-10k.pdf'
        m = re.match(r"^([A-Za-z]{1,5})[_\-\s]", Path(filename).name)
        if m:
            ticker = m.group(1).upper()
            if ticker not in ["FORM", "DOC", "PDF", "FILE", "NEW"]:
                return ticker

        return None

    def detect_document_type(self, text: str, filename: str) -> str | None:
        """Identifies standard financial report types."""
        combined = f"{filename} {text[:2000]}"
        for pattern, doc_type in self.DOCUMENT_TYPE_MAP:
            if re.search(pattern, combined, re.IGNORECASE):
                return doc_type
        return "Financial Document"

    def detect_reporting_period(self, text: str, filename: str) -> str | None:
        """Extracts Q1, Q2, Q3, Q4, Full Year, FY."""
        combined = f"{filename} {text[:3000]}"
        
        # Check for quarterly
        q_match = re.search(r"\b(Q[1-4]|first\s+quarter|second\s+quarter|third\s+quarter|fourth\s+quarter)\b", combined, re.IGNORECASE)
        if q_match:
            q_val = q_match.group(1).upper()
            if "FIRST" in q_val: return "Q1"
            if "SECOND" in q_val: return "Q2"
            if "THIRD" in q_val: return "Q3"
            if "FOURTH" in q_val: return "Q4"
            return q_val

        # Check for annual / full year
        if re.search(r"\b(annual|full\s+year|10-k|fiscal\s+year)\b", combined, re.IGNORECASE):
            return "Full Year"

        return "FY"

    def detect_fiscal_year(self, text: str, filename: str) -> str | None:
        """Extracts 4-digit fiscal year (e.g. 2024, 2023)."""
        combined = f"{filename} {text[:3000]}"
        
        # Look for explicit FY2024 or year ended 2024
        m = re.search(r"\b(?:FY|Fiscal\s+Year|Year\s+Ended[^\n\d]*)\s*(\d{4})\b", combined, re.IGNORECASE)
        if m:
            return m.group(1)

        # Look for any recent 4-digit year 2018-2030
        years = re.findall(r"\b(20[12]\d)\b", combined)
        if years:
            # Return the most frequent or first recognized year
            return years[0]

        return None

    def merge_with_user_provided(self, extracted: dict, user_provided: dict) -> dict:
        """User-provided values always override auto-extracted values."""
        final_data = {}
        for k, v in extracted.items():
            final_data[k] = v
        for k, v in user_provided.items():
            if v:  # Only override if user provided a non-empty string
                final_data[k] = v
        return final_data
