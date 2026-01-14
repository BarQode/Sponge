"""
Ticketing System Integration - Jira and ServiceNow

Integrates with ticketing systems to:
- Track toil tasks automatically
- Create tickets from alerts
- Tag tickets for toil analysis
- Auto-close tickets when issues are auto-remediated
"""

import logging
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from datetime import datetime
import json
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class TicketingClient(ABC):
    """Abstract base class for ticketing system clients"""

    @abstractmethod
    def create_ticket(self,
                     title: str,
                     description: str,
                     priority: str,
                     labels: List[str] = None,
                     assignee: str = None) -> Optional[str]:
        """Create a new ticket"""
        pass

    @abstractmethod
    def update_ticket(self, ticket_id: str, fields: Dict[str, Any]) -> bool:
        """Update an existing ticket"""
        pass

    @abstractmethod
    def close_ticket(self, ticket_id: str, resolution: str) -> bool:
        """Close a ticket"""
        pass

    @abstractmethod
    def add_comment(self, ticket_id: str, comment: str) -> bool:
        """Add a comment to a ticket"""
        pass

    @abstractmethod
    def search_tickets(self, query: str) -> List[Dict[str, Any]]:
        """Search for tickets"""
        pass

    @abstractmethod
    def tag_toil(self, ticket_id: str) -> bool:
        """Tag a ticket as toil for tracking"""
        pass


class JiraClient(TicketingClient):
    """
    Jira integration client

    Handles Jira-specific API calls and ticket management
    """

    def __init__(self,
                 url: str,
                 username: str,
                 api_token: str,
                 project_key: str):
        self.url = url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.project_key = project_key
        self.auth = HTTPBasicAuth(username, api_token)
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

    def create_ticket(self,
                     title: str,
                     description: str,
                     priority: str = "Medium",
                     labels: List[str] = None,
                     assignee: str = None) -> Optional[str]:
        """
        Create a Jira issue

        Args:
            title: Issue summary
            description: Issue description
            priority: Priority level (Highest, High, Medium, Low, Lowest)
            labels: List of labels
            assignee: Username of assignee

        Returns:
            Issue key (e.g., PROJ-123) or None if failed
        """
        try:
            payload = {
                "fields": {
                    "project": {"key": self.project_key},
                    "summary": title,
                    "description": description,
                    "issuetype": {"name": "Task"},
                    "priority": {"name": priority}
                }
            }

            if labels:
                payload["fields"]["labels"] = labels

            if assignee:
                payload["fields"]["assignee"] = {"name": assignee}

            response = requests.post(
                f"{self.url}/rest/api/3/issue",
                json=payload,
                auth=self.auth,
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 201:
                issue_key = response.json().get('key')
                logger.info(f"Created Jira issue: {issue_key}")
                return issue_key
            else:
                logger.error(f"Failed to create Jira issue: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating Jira issue: {e}")
            return None

    def update_ticket(self, ticket_id: str, fields: Dict[str, Any]) -> bool:
        """
        Update a Jira issue

        Args:
            ticket_id: Issue key (e.g., PROJ-123)
            fields: Dictionary of fields to update

        Returns:
            True if successful
        """
        try:
            payload = {"fields": fields}

            response = requests.put(
                f"{self.url}/rest/api/3/issue/{ticket_id}",
                json=payload,
                auth=self.auth,
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 204:
                logger.info(f"Updated Jira issue: {ticket_id}")
                return True
            else:
                logger.error(f"Failed to update Jira issue: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error updating Jira issue: {e}")
            return False

    def close_ticket(self, ticket_id: str, resolution: str = "Done") -> bool:
        """
        Close a Jira issue

        Args:
            ticket_id: Issue key
            resolution: Resolution name

        Returns:
            True if successful
        """
        try:
            # Transition to "Done" status (usually ID 31 or 21)
            # Get available transitions first
            response = requests.get(
                f"{self.url}/rest/api/3/issue/{ticket_id}/transitions",
                auth=self.auth,
                headers=self.headers,
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"Failed to get transitions: {response.text}")
                return False

            transitions = response.json().get('transitions', [])
            done_transition = None

            for transition in transitions:
                if transition['name'].lower() in ['done', 'close', 'closed', 'resolve']:
                    done_transition = transition['id']
                    break

            if not done_transition:
                logger.error(f"No 'Done' transition found for {ticket_id}")
                return False

            # Perform transition
            payload = {
                "transition": {"id": done_transition},
                "fields": {
                    "resolution": {"name": resolution}
                }
            }

            response = requests.post(
                f"{self.url}/rest/api/3/issue/{ticket_id}/transitions",
                json=payload,
                auth=self.auth,
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 204:
                logger.info(f"Closed Jira issue: {ticket_id}")
                return True
            else:
                logger.error(f"Failed to close Jira issue: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error closing Jira issue: {e}")
            return False

    def add_comment(self, ticket_id: str, comment: str) -> bool:
        """
        Add a comment to a Jira issue

        Args:
            ticket_id: Issue key
            comment: Comment text

        Returns:
            True if successful
        """
        try:
            payload = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": comment
                                }
                            ]
                        }
                    ]
                }
            }

            response = requests.post(
                f"{self.url}/rest/api/3/issue/{ticket_id}/comment",
                json=payload,
                auth=self.auth,
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 201:
                logger.info(f"Added comment to Jira issue: {ticket_id}")
                return True
            else:
                logger.error(f"Failed to add comment: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error adding comment: {e}")
            return False

    def search_tickets(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for Jira issues

        Args:
            query: JQL query string

        Returns:
            List of issue dictionaries
        """
        try:
            payload = {
                "jql": query,
                "maxResults": 100,
                "fields": ["summary", "status", "priority", "assignee", "created", "labels"]
            }

            response = requests.post(
                f"{self.url}/rest/api/3/search",
                json=payload,
                auth=self.auth,
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 200:
                issues = response.json().get('issues', [])
                return [
                    {
                        'key': issue['key'],
                        'summary': issue['fields']['summary'],
                        'status': issue['fields']['status']['name'],
                        'priority': issue['fields']['priority']['name'],
                        'labels': issue['fields'].get('labels', [])
                    }
                    for issue in issues
                ]
            else:
                logger.error(f"Failed to search Jira issues: {response.text}")
                return []

        except Exception as e:
            logger.error(f"Error searching Jira issues: {e}")
            return []

    def tag_toil(self, ticket_id: str) -> bool:
        """
        Tag a Jira issue as toil

        Args:
            ticket_id: Issue key

        Returns:
            True if successful
        """
        return self.update_ticket(ticket_id, {
            "labels": [{"add": "toil"}, {"add": "automation-candidate"}]
        })

    def get_toil_tickets(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get all toil-tagged tickets from the last N days"""
        query = f"project = {self.project_key} AND labels = toil AND created >= -{days}d"
        return self.search_tickets(query)


class ServiceNowClient(TicketingClient):
    """
    ServiceNow integration client

    Handles ServiceNow-specific API calls and incident management
    """

    def __init__(self,
                 instance_url: str,
                 username: str,
                 password: str):
        self.instance_url = instance_url.rstrip('/')
        self.username = username
        self.password = password
        self.auth = HTTPBasicAuth(username, password)
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

    def create_ticket(self,
                     title: str,
                     description: str,
                     priority: str = "3",
                     labels: List[str] = None,
                     assignee: str = None) -> Optional[str]:
        """
        Create a ServiceNow incident

        Args:
            title: Short description
            description: Description
            priority: Priority (1=Critical, 2=High, 3=Medium, 4=Low)
            labels: List of labels (stored in comments)
            assignee: User ID of assignee

        Returns:
            Incident number (e.g., INC0010001) or None if failed
        """
        try:
            payload = {
                "short_description": title,
                "description": description,
                "priority": priority,
                "category": "software",
                "subcategory": "automation"
            }

            if assignee:
                payload["assigned_to"] = assignee

            if labels:
                payload["work_notes"] = f"Labels: {', '.join(labels)}"

            response = requests.post(
                f"{self.instance_url}/api/now/table/incident",
                json=payload,
                auth=self.auth,
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 201:
                incident_number = response.json()['result']['number']
                logger.info(f"Created ServiceNow incident: {incident_number}")
                return incident_number
            else:
                logger.error(f"Failed to create ServiceNow incident: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating ServiceNow incident: {e}")
            return None

    def update_ticket(self, ticket_id: str, fields: Dict[str, Any]) -> bool:
        """
        Update a ServiceNow incident

        Args:
            ticket_id: Incident number or sys_id
            fields: Dictionary of fields to update

        Returns:
            True if successful
        """
        try:
            response = requests.patch(
                f"{self.instance_url}/api/now/table/incident/{ticket_id}",
                json=fields,
                auth=self.auth,
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"Updated ServiceNow incident: {ticket_id}")
                return True
            else:
                logger.error(f"Failed to update ServiceNow incident: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error updating ServiceNow incident: {e}")
            return False

    def close_ticket(self, ticket_id: str, resolution: str = "Automated fix applied") -> bool:
        """
        Close a ServiceNow incident

        Args:
            ticket_id: Incident number or sys_id
            resolution: Resolution notes

        Returns:
            True if successful
        """
        return self.update_ticket(ticket_id, {
            "state": "6",  # Resolved
            "close_code": "Solved (Permanently)",
            "close_notes": resolution
        })

    def add_comment(self, ticket_id: str, comment: str) -> bool:
        """
        Add a work note to a ServiceNow incident

        Args:
            ticket_id: Incident number or sys_id
            comment: Comment text

        Returns:
            True if successful
        """
        return self.update_ticket(ticket_id, {
            "work_notes": comment
        })

    def search_tickets(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for ServiceNow incidents

        Args:
            query: Encoded query string

        Returns:
            List of incident dictionaries
        """
        try:
            response = requests.get(
                f"{self.instance_url}/api/now/table/incident",
                params={"sysparm_query": query, "sysparm_limit": 100},
                auth=self.auth,
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 200:
                incidents = response.json().get('result', [])
                return [
                    {
                        'number': inc['number'],
                        'short_description': inc['short_description'],
                        'state': inc['state'],
                        'priority': inc['priority'],
                        'sys_id': inc['sys_id']
                    }
                    for inc in incidents
                ]
            else:
                logger.error(f"Failed to search ServiceNow incidents: {response.text}")
                return []

        except Exception as e:
            logger.error(f"Error searching ServiceNow incidents: {e}")
            return []

    def tag_toil(self, ticket_id: str) -> bool:
        """
        Tag a ServiceNow incident as toil

        Args:
            ticket_id: Incident number or sys_id

        Returns:
            True if successful
        """
        return self.add_comment(ticket_id, "[TOIL] [AUTOMATION-CANDIDATE]")


class TicketingIntegration:
    """
    High-level integration for ticketing systems

    Provides unified interface for managing tickets across platforms
    """

    def __init__(self, client: TicketingClient):
        self.client = client

    def create_alert_ticket(self,
                           alert_message: str,
                           severity: str,
                           slo_name: str,
                           auto_tag_toil: bool = True) -> Optional[str]:
        """
        Create a ticket from an alert

        Args:
            alert_message: Alert message
            severity: Alert severity
            slo_name: SLO name that triggered alert
            auto_tag_toil: Whether to automatically tag as toil

        Returns:
            Ticket ID or None
        """
        priority_map = {
            'page': 'Highest',
            'critical': 'High',
            'warning': 'Medium',
            'info': 'Low'
        }

        priority = priority_map.get(severity, 'Medium')
        labels = ['alert', 'slo', slo_name]

        if auto_tag_toil:
            labels.append('toil')

        ticket_id = self.client.create_ticket(
            title=f"[{severity.upper()}] {slo_name}: SLO threshold exceeded",
            description=alert_message,
            priority=priority,
            labels=labels
        )

        return ticket_id

    def close_remediated_ticket(self,
                                ticket_id: str,
                                runbook_name: str,
                                execution_time: float) -> bool:
        """
        Close a ticket that was auto-remediated

        Args:
            ticket_id: Ticket to close
            runbook_name: Runbook that was executed
            execution_time: Time taken (seconds)

        Returns:
            True if successful
        """
        resolution = (
            f"Auto-remediated using runbook: {runbook_name}\n"
            f"Execution time: {execution_time:.2f} seconds\n"
            f"Resolved at: {datetime.now().isoformat()}"
        )

        return self.client.close_ticket(ticket_id, resolution)

    def track_manual_intervention(self,
                                  ticket_id: str,
                                  task_description: str,
                                  time_spent: float) -> bool:
        """
        Track manual intervention time for toil analysis

        Args:
            ticket_id: Ticket ID
            task_description: What was done manually
            time_spent: Time spent in hours

        Returns:
            True if successful
        """
        comment = (
            f"[TOIL TRACKING]\n"
            f"Manual intervention required\n"
            f"Task: {task_description}\n"
            f"Time spent: {time_spent:.2f} hours\n"
            f"Automation candidate: Yes\n"
            f"Timestamp: {datetime.now().isoformat()}"
        )

        success = self.client.add_comment(ticket_id, comment)

        if success:
            self.client.tag_toil(ticket_id)

        return success
