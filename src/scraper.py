"""
Web scraper for finding solutions to error patterns.
Intelligently searches the web and aggregates solutions from multiple sources.
Integrates with ML-based fix prediction for production-ready bug resolution.
"""

import logging
import time
from typing import Dict, List, Any, Optional
from duckduckgo_search import DDGS
from src.config import SCRAPER_CONFIG
from src.ml_engine import HybridMLEngine, clean_log

# Configure logging
logger = logging.getLogger(__name__)


class SolutionScraper:
    """
    Intelligent web scraper for finding error solutions with detailed implementation steps.

    Features:
    - ML-based fix prediction using Random Forest
    - Retry logic with exponential backoff
    - Multiple result aggregation
    - Quality scoring based on source relevance
    - Detailed step-by-step implementation extraction
    - Fallback handling
    """

    def __init__(self):
        """Initialize the solution scraper with configuration and ML engine."""
        self.max_retries = SCRAPER_CONFIG["max_retries"]
        self.retry_delay = SCRAPER_CONFIG["retry_delay"]
        self.max_results = SCRAPER_CONFIG["max_results"]
        self.timeout = SCRAPER_CONFIG["timeout"]

        # Initialize ML engine for fix prediction
        self.ml_engine = HybridMLEngine()

        # Trusted sources for technical solutions (for scoring)
        self.trusted_sources = [
            'stackoverflow.com',
            'stackexchange.com',
            'github.com',
            'microsoft.com',
            'docs.python.org',
            'developer.mozilla.org',
            'aws.amazon.com',
            'cloud.google.com',
            'docs.aws.amazon.com',
            'learn.microsoft.com',
            'redis.io',
            'mongodb.com',
            'postgresql.org'
        ]

        logger.info("SolutionScraper initialized with ML engine")

    def _score_result(self, result: Dict[str, str]) -> int:
        """
        Score a search result based on source quality.

        Args:
            result: Dictionary with 'href' and 'body' keys

        Returns:
            Integer score (higher is better)
        """
        score = 0
        url = result.get('href', '').lower()

        # Check if from trusted source
        for source in self.trusted_sources:
            if source in url:
                score += 10
                break

        # Bonus for stackoverflow (most reliable for errors)
        if 'stackoverflow.com' in url:
            score += 5

        # Check body for quality indicators
        body = result.get('body', '').lower()
        quality_keywords = ['solution', 'fix', 'resolved', 'answer', 'workaround', 'solved']

        for keyword in quality_keywords:
            if keyword in body:
                score += 2

        return score

    def find_solution(self, error_message: str, severity: str = "medium") -> Dict[str, Any]:
        """
        Searches the web for a solution to the specific error message.
        Combines ML-based fix prediction with web search results.

        Args:
            error_message: The error pattern to search for
            severity: Severity level of the error (critical, high, medium, low, info)

        Returns:
            Dictionary with 'solution', 'source', 'confidence', and 'ml_recommendation' keys
        """
        if not error_message or not error_message.strip():
            logger.warning("Empty error message provided to scraper")
            return {
                "solution": "No error message provided.",
                "source": "N/A",
                "confidence": "low",
                "all_sources": [],
                "ml_recommendation": None
            }

        # Get ML-based fix prediction first
        ml_recommendation = self._get_ml_recommendation(error_message, severity)

        # Build search query
        query = self._build_query(error_message)
        logger.info(f"Searching for solution: '{query}'")

        # Try to get results with retry logic
        results = self._search_with_retry(query)

        if not results:
            logger.warning(f"No results found for: {error_message}")
            return {
                "solution": "No specific solution found on the public web. Consider checking internal documentation or contacting support.",
                "source": "N/A",
                "confidence": "low",
                "all_sources": [],
                "ml_recommendation": ml_recommendation
            }

        # Aggregate and score results
        aggregated = self._aggregate_results(results)
        aggregated["ml_recommendation"] = ml_recommendation

        return aggregated

    def _build_query(self, error_message: str) -> str:
        """
        Build an optimized search query from the error message.

        Args:
            error_message: Raw error pattern

        Returns:
            Optimized search query string
        """
        # Extract key error terms (remove generic tokens)
        query = error_message.replace('<IP>', '').replace('<NUM>', '')
        query = query.replace('<HEX>', '').replace('<TIMESTAMP>', '')
        query = query.replace('<PATH>', '').replace('<UUID>', '')
        query = query.strip()

        # Add search modifiers for better results
        query = f"{query} solution fix stackoverflow"

        return query

    def _search_with_retry(self, query: str) -> List[Dict[str, str]]:
        """
        Execute search with retry logic.

        Args:
            query: Search query string

        Returns:
            List of search result dictionaries
        """
        for attempt in range(self.max_retries):
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=self.max_results))

                    if results:
                        logger.info(f"Found {len(results)} results for query")
                        return results
                    else:
                        logger.debug(f"No results on attempt {attempt + 1}")

            except Exception as e:
                logger.warning(f"Search attempt {attempt + 1} failed: {e}")

                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    logger.debug(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} search attempts failed")

        return []

    def _aggregate_results(self, results: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Aggregate multiple search results into a single solution.

        Args:
            results: List of search result dictionaries

        Returns:
            Aggregated solution dictionary
        """
        if not results:
            return {
                "solution": "No results to aggregate.",
                "source": "N/A",
                "confidence": "low",
                "all_sources": []
            }

        # Score all results
        scored_results = [(self._score_result(r), r) for r in results]
        scored_results.sort(key=lambda x: x[0], reverse=True)

        # Get best result
        best_score, best_result = scored_results[0]

        # Determine confidence based on score
        if best_score >= 15:
            confidence = "high"
        elif best_score >= 8:
            confidence = "medium"
        else:
            confidence = "low"

        # Build comprehensive solution from top results
        all_sources = []
        solution_parts = []

        for score, result in scored_results[:3]:  # Top 3 results
            body = result.get('body', 'No description available.')
            href = result.get('href', 'Unknown Source')

            solution_parts.append(body)
            all_sources.append({
                "url": href,
                "snippet": body[:200] + "..." if len(body) > 200 else body,
                "score": score
            })

        # Combine solutions
        main_solution = solution_parts[0] if solution_parts else "No solution available."

        # Extract detailed implementation steps
        implementation_steps = self._extract_implementation_steps(solution_parts)

        return {
            "solution": main_solution,
            "source": best_result.get('href', 'Unknown Source'),
            "confidence": confidence,
            "all_sources": all_sources,
            "implementation_steps": implementation_steps
        }

    def _extract_implementation_steps(self, solution_texts: List[str]) -> List[str]:
        """
        Extract detailed step-by-step implementation instructions from solution text.

        Args:
            solution_texts: List of solution text snippets

        Returns:
            List of implementation steps
        """
        steps = []
        combined_text = " ".join(solution_texts)

        # Common step indicators
        step_indicators = [
            r'step \d+[:.]\s*(.+?)(?=step \d+|$)',
            r'\d+\.\s*(.+?)(?=\d+\.|$)',
            r'first,?\s*(.+?)(?=second|then|next|finally|$)',
            r'then,?\s*(.+?)(?=then|next|finally|$)',
            r'next,?\s*(.+?)(?=next|then|finally|$)',
            r'finally,?\s*(.+?)$'
        ]

        # Look for numbered steps or sequential instructions
        import re

        for pattern in step_indicators:
            matches = re.finditer(pattern, combined_text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                step = match.group(1).strip()
                if step and len(step) > 10 and len(step) < 500:
                    steps.append(step)

        # If no structured steps found, create generic steps
        if not steps:
            steps = [
                "Review the error message and identify the root cause",
                "Check the solution documentation linked in the source",
                "Implement the recommended fix based on the solution description",
                "Test the fix in a development environment",
                "Deploy to production after verification"
            ]

        # Remove duplicates while preserving order
        seen = set()
        unique_steps = []
        for step in steps:
            step_lower = step.lower()
            if step_lower not in seen:
                seen.add(step_lower)
                unique_steps.append(step)

        return unique_steps[:10]  # Limit to 10 steps

    def _get_ml_recommendation(self, error_message: str, severity: str) -> Dict[str, Any]:
        """
        Get ML-based fix recommendation using Random Forest classifier.

        Args:
            error_message: Error pattern
            severity: Severity level

        Returns:
            Dictionary with ML fix prediction, confidence, and implementation steps
        """
        try:
            # Clean the error message
            cleaned = clean_log(error_message)

            # Get prediction from ML engine
            prediction = self.ml_engine.bug_fix_classifier.predict(cleaned, severity)

            # Get implementation steps from ML engine
            fix_action = prediction.get("recommended_fix", "ignore_transient")
            from src.ml_engine import _FIX_STEPS
            implementation_steps = _FIX_STEPS.get(fix_action, [])

            logger.info(f"ML recommendation: {fix_action} (confidence: {prediction.get('confidence', 0):.2f})")

            return {
                "recommended_fix": fix_action,
                "confidence": prediction.get("confidence", 0.0),
                "alternatives": prediction.get("alternatives", []),
                "implementation_steps": implementation_steps,
                "source": prediction.get("source", "ml_model")
            }

        except Exception as e:
            logger.error(f"Error getting ML recommendation: {e}")
            return {
                "recommended_fix": "escalate_to_oncall",
                "confidence": 0.5,
                "alternatives": [],
                "implementation_steps": [],
                "source": "fallback"
            }

    def batch_find_solutions(self, error_messages: List[str], severities: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Find solutions for multiple error messages with ML-based recommendations.

        Args:
            error_messages: List of error patterns
            severities: Optional list of severity levels (defaults to "medium")

        Returns:
            List of solution dictionaries with ML recommendations
        """
        logger.info(f"Batch searching for {len(error_messages)} errors")

        # Default severity if not provided
        if severities is None:
            severities = ["medium"] * len(error_messages)

        # Ensure equal lengths
        if len(severities) != len(error_messages):
            logger.warning(f"Severity list length mismatch, using default 'medium'")
            severities = ["medium"] * len(error_messages)

        solutions = []
        for i, (error, severity) in enumerate(zip(error_messages, severities)):
            logger.info(f"Processing error {i + 1}/{len(error_messages)}")

            solution = self.find_solution(error, severity)
            solutions.append(solution)

            # Rate limiting
            if i < len(error_messages) - 1:
                time.sleep(1)  # Be respectful to search engines

        return solutions

    def analyze_with_ml(self, error_messages: List[str], severities: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Perform ML-only analysis without web scraping.
        Useful for fast, offline bug detection and fix recommendations.

        Args:
            error_messages: List of error patterns
            severities: Optional list of severity levels

        Returns:
            List of ML-based recommendations
        """
        logger.info(f"Performing ML analysis on {len(error_messages)} errors")

        if severities is None:
            severities = ["medium"] * len(error_messages)

        recommendations = []
        for error, severity in zip(error_messages, severities):
            ml_rec = self._get_ml_recommendation(error, severity)
            recommendations.append(ml_rec)

        return recommendations
