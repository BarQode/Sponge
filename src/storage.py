"""
Knowledge Base storage management using Excel.
Provides caching and persistence for error solutions.
"""

import pandas as pd
import os
import logging
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
from pathlib import Path
from src.config import KNOWLEDGE_BASE_FILE

# Configure logging
logger = logging.getLogger(__name__)


class KnowledgeBase:
    """
    Manages the local knowledge base stored as an Excel spreadsheet.

    Features:
    - Automatic initialization
    - Cache lookup for known errors
    - Deduplication
    - Update tracking with timestamps
    - Export capabilities
    """

    def __init__(self, filename: Optional[str] = None):
        """
        Initialize the knowledge base.

        Args:
            filename: Path to Excel file (uses config default if not provided)
        """
        self.filename = filename or KNOWLEDGE_BASE_FILE
        self.file_path = Path(self.filename)

        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()
        logger.info(f"KnowledgeBase initialized at: {self.filename}")

    def _init_db(self):
        """Initialize the database file if it doesn't exist."""
        if not self.file_path.exists():
            logger.info("Creating new knowledge base file")
            df = pd.DataFrame(columns=[
                "Timestamp",
                "Category",  # CPU, Memory, Latency, Zombie, Error
                "Issue_Type",  # Specific type of issue
                "Severity",  # critical, high, medium, low
                "Error_Pattern",
                "Frequency",
                "Solution",
                "Source",
                "Confidence",
                "Implementation_Steps",  # JSON string of steps
                "Recommendations",  # JSON string of recommendations
                "Last_Updated"
            ])
            try:
                df.to_excel(self.filename, index=False, engine='openpyxl')
                logger.info(f"Knowledge base created: {self.filename}")
            except Exception as e:
                logger.error(f"Failed to create knowledge base: {e}")
                raise
        else:
            logger.debug(f"Using existing knowledge base: {self.filename}")

    def check_cache(self, error_pattern: str) -> Optional[Dict[str, Any]]:
        """
        Check if we already have a solution for this error pattern.

        Args:
            error_pattern: The normalized error message

        Returns:
            Dictionary with solution info if found, None otherwise
        """
        if not error_pattern or not error_pattern.strip():
            logger.warning("Empty error pattern provided to cache check")
            return None

        try:
            df = pd.read_excel(self.filename, engine='openpyxl')

            if df.empty:
                logger.debug("Knowledge base is empty")
                return None

            # Case-insensitive match
            match = df[df['Error_Pattern'].str.lower() == error_pattern.lower()]

            if not match.empty:
                row = match.iloc[0]
                logger.info(f"Cache hit for error: {error_pattern[:50]}...")

                return {
                    "solution": row['Solution'],
                    "source": row['Source'],
                    "confidence": row.get('Confidence', 'medium'),
                    "frequency": int(row.get('Frequency', 1)),
                    "last_updated": row.get('Last_Updated', 'Unknown')
                }
            else:
                logger.debug(f"Cache miss for error: {error_pattern[:50]}...")
                return None

        except FileNotFoundError:
            logger.warning("Knowledge base file not found, reinitializing")
            self._init_db()
            return None
        except Exception as e:
            logger.error(f"Error reading knowledge base: {e}")
            return None

    def save_entry(self, error: str, fix: str, source: str, count: int = 1,
                   confidence: str = "medium", category: str = "Error",
                   issue_type: str = "general", severity: str = "medium",
                   implementation_steps: Optional[List[str]] = None,
                   recommendations: Optional[List[str]] = None) -> bool:
        """
        Save a new resolution to the spreadsheet or update existing.

        Args:
            error: Error pattern
            fix: Solution description
            source: URL or reference for the solution
            count: Number of occurrences
            confidence: Confidence level (low, medium, high)
            category: Issue category (CPU, Memory, Latency, Zombie, Error)
            issue_type: Specific type of issue
            severity: Severity level (critical, high, medium, low)
            implementation_steps: List of implementation steps
            recommendations: List of recommendations

        Returns:
            True if successful, False otherwise
        """
        if not error or not error.strip():
            logger.warning("Cannot save empty error pattern")
            return False

        try:
            df = pd.read_excel(self.filename, engine='openpyxl')

            # Check if error already exists
            existing = df[df['Error_Pattern'].str.lower() == error.lower()]

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Serialize lists to JSON strings
            steps_json = json.dumps(implementation_steps) if implementation_steps else "[]"
            recommendations_json = json.dumps(recommendations) if recommendations else "[]"

            if not existing.empty:
                # Update existing entry
                idx = existing.index[0]
                old_count = int(df.loc[idx, 'Frequency'])
                new_count = old_count + count

                df.loc[idx, 'Frequency'] = new_count
                df.loc[idx, 'Category'] = category
                df.loc[idx, 'Issue_Type'] = issue_type
                df.loc[idx, 'Severity'] = severity
                df.loc[idx, 'Solution'] = fix
                df.loc[idx, 'Source'] = source
                df.loc[idx, 'Confidence'] = confidence
                df.loc[idx, 'Implementation_Steps'] = steps_json
                df.loc[idx, 'Recommendations'] = recommendations_json
                df.loc[idx, 'Last_Updated'] = timestamp

                logger.info(f"Updated existing entry: {error[:50]}... (count: {old_count} → {new_count})")
            else:
                # Create new entry
                new_data = {
                    "Timestamp": timestamp,
                    "Category": category,
                    "Issue_Type": issue_type,
                    "Severity": severity,
                    "Error_Pattern": error,
                    "Frequency": count,
                    "Solution": fix,
                    "Source": source,
                    "Confidence": confidence,
                    "Implementation_Steps": steps_json,
                    "Recommendations": recommendations_json,
                    "Last_Updated": timestamp
                }

                df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                logger.info(f"Added new entry: {error[:50]}...")

            # Save back to Excel
            df.to_excel(self.filename, index=False, engine='openpyxl')
            return True

        except Exception as e:
            logger.error(f"Failed to save entry to knowledge base: {e}")
            return False

    def get_top_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most frequent errors from the knowledge base.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of error dictionaries sorted by frequency
        """
        try:
            df = pd.read_excel(self.filename, engine='openpyxl')

            if df.empty:
                return []

            # Sort by frequency
            df_sorted = df.sort_values('Frequency', ascending=False).head(limit)

            results = []
            for _, row in df_sorted.iterrows():
                results.append({
                    "error_pattern": row['Error_Pattern'],
                    "frequency": int(row['Frequency']),
                    "solution": row['Solution'],
                    "source": row['Source'],
                    "confidence": row.get('Confidence', 'medium')
                })

            return results

        except Exception as e:
            logger.error(f"Error retrieving top errors: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge base.

        Returns:
            Dictionary with statistics
        """
        try:
            df = pd.read_excel(self.filename, engine='openpyxl')

            if df.empty:
                return {
                    "total_patterns": 0,
                    "total_occurrences": 0,
                    "avg_frequency": 0,
                    "high_confidence_count": 0
                }

            stats = {
                "total_patterns": len(df),
                "total_occurrences": int(df['Frequency'].sum()),
                "avg_frequency": float(df['Frequency'].mean()),
                "high_confidence_count": len(df[df['Confidence'] == 'high']),
                "medium_confidence_count": len(df[df['Confidence'] == 'medium']),
                "low_confidence_count": len(df[df['Confidence'] == 'low'])
            }

            return stats

        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            return {"error": str(e)}

    def export_to_csv(self, output_path: str) -> bool:
        """
        Export the knowledge base to CSV format.

        Args:
            output_path: Path for the CSV file

        Returns:
            True if successful, False otherwise
        """
        try:
            df = pd.read_excel(self.filename, engine='openpyxl')
            df.to_csv(output_path, index=False)
            logger.info(f"Exported knowledge base to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            return False

    def clear_all(self) -> bool:
        """
        Clear all entries from the knowledge base.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.warning("Clearing all knowledge base entries")
            df = pd.DataFrame(columns=[
                "Timestamp",
                "Error_Pattern",
                "Frequency",
                "Solution",
                "Source",
                "Confidence",
                "Last_Updated"
            ])
            df.to_excel(self.filename, index=False, engine='openpyxl')
            return True
        except Exception as e:
            logger.error(f"Failed to clear knowledge base: {e}")
            return False
