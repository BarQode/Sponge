"""
Web scraper for finding solutions to error patterns.
Intelligently searches the web and aggregates solutions from multiple sources.
"""

import logging
import time
from typing import Dict, List, Any, Optional
from duckduckgo_search import DDGS
from src.config import SCRAPER_CONFIG

# Configure logging
logger = logging.getLogger(__name__)


class SolutionScraper:
    """
    Intelligent web scraper for finding error solutions.

    Features:
    - Retry logic with exponential backoff
    - Multiple result aggregation
    - Quality scoring based on source relevance
    - Fallback handling
    """

    def __init__(self):
        """Initialize the solution scraper with configuration."""
        self.max_retries = SCRAPER_CONFIG["max_retries"]
        self.retry_delay = SCRAPER_CONFIG["retry_delay"]
        self.max_results = SCRAPER_CONFIG["max_results"]
        self.timeout = SCRAPER_CONFIG["timeout"]

        # Trusted sources for technical solutions (for scoring)
        self.trusted_sources = [
            'stackoverflow.com',
            'stackexchange.com',
            'github.com',
            'microsoft.com',
            'docs.python.org',
            'developer.mozilla.org',
            'aws.amazon.com',
            'cloud.google.com'
        ]

        logger.info("SolutionScraper initialized")

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

    def find_solution(self, error_message: str) -> Dict[str, Any]:
        """
        Searches the web for a solution to the specific error message.

        Args:
            error_message: The error pattern to search for

        Returns:
            Dictionary with 'solution', 'source', and 'confidence' keys
        """
        if not error_message or not error_message.strip():
            logger.warning("Empty error message provided to scraper")
            return {
                "solution": "No error message provided.",
                "source": "N/A",
                "confidence": "low",
                "all_sources": []
            }

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
                "all_sources": []
            }

        # Aggregate and score results
        return self._aggregate_results(results)

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

        return {
            "solution": main_solution,
            "source": best_result.get('href', 'Unknown Source'),
            "confidence": confidence,
            "all_sources": all_sources
        }

    def batch_find_solutions(self, error_messages: List[str]) -> List[Dict[str, Any]]:
        """
        Find solutions for multiple error messages.

        Args:
            error_messages: List of error patterns

        Returns:
            List of solution dictionaries
        """
        logger.info(f"Batch searching for {len(error_messages)} errors")

        solutions = []
        for i, error in enumerate(error_messages):
            logger.info(f"Processing error {i + 1}/{len(error_messages)}")

            solution = self.find_solution(error)
            solutions.append(solution)

            # Rate limiting
            if i < len(error_messages) - 1:
                time.sleep(1)  # Be respectful to search engines

        return solutions
